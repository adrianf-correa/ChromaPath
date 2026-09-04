import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from PIL import Image, ImageOps

from src.color_analysis import (
    analyze_neighbor_differences,
    analyze_transparency,
    find_near_black_masks,
)
from src.vectorize import vectorize_image


MIN_FILTER_DELTA_E = 0.75
MAX_FILTER_DELTA_E = 3.0
NOISE_MARGIN = 1.25
BILATERAL_DIAMETER = 5
BILATERAL_SPATIAL_SIGMA = 3.0
FLAT_IMAGE_IDENTICAL_NEIGHBORS = 85.0
NOISE_WITHIN_THREE_NEIGHBORS = 97.0
NEAR_OPAQUE_VISIBLE_PIXELS = 95.0
LOW_ALPHA_FRINGE_LIMIT = 31
DEFAULT_FILTER_SPECKLE = 4
OPAQUE_FRINGE_FILTER_SPECKLE = 16
OPAQUE_FRINGE_MIN_VISIBLE_PIXELS = 100_000
OPAQUE_FRINGE_MIN_UNIQUE_COLORS = 1_000
BACKGROUND_BORDER_DELTA_E = 3.0
BACKGROUND_FOREGROUND_DELTA_E = 6.0
BACKGROUND_MIN_BORDER_COVERAGE = 95.0
ISOLATED_COMPONENT_AREA_RATIO = 0.0001
MIN_ISOLATED_COMPONENT_AREA = 4
MAIN_COMPONENT_MIN_AREA_RATIO = 0.01
NEAR_MAIN_PROTECTION_RATIO = 0.015
NOISY_BACKGROUND_FILTER_SPECKLE = 32
NOISY_BACKGROUND_MIN_REMOVED_COMPONENTS = 8
SILHOUETTE_OPENING_RATIO = 0.017
MIN_SILHOUETTE_KERNEL_SIZE = 5
MAX_SILHOUETTE_KERNEL_SIZE = 21
MIN_PROTRUSION_AREA = 4
REPEATED_DETAIL_MIN_COUNT = 3
REPEATED_DETAIL_MIN_AREA_RATIO = 0.5
REPEATED_DETAIL_AREA_TOLERANCE = 0.25
REPEATED_DETAIL_COLOR_DELTA_E = 3.0
REPEATED_DETAIL_CLUSTER_RATIO = 0.12
REPEATED_DETAIL_ALIGNMENT_RATIO = 0.01
REPEATED_DETAIL_SPACING_RATIO = 1.5


def estimate_filter_delta_e(neighbor_analysis: dict) -> float:
    """Estima um limite conservador a partir da variacao local da imagem."""
    estimated_delta_e = neighbor_analysis["positive_percentile_95"] * NOISE_MARGIN
    return min(MAX_FILTER_DELTA_E, max(MIN_FILTER_DELTA_E, estimated_delta_e))


def should_apply_bilateral_filter(neighbor_analysis: dict) -> bool:
    """Decide se a imagem tem variacao local suficiente para justificar o filtro."""
    identical_percentage = neighbor_analysis["identical_percentage"]
    within_three_percentage = neighbor_analysis["within_three_percentage"]
    return (
        identical_percentage < FLAT_IMAGE_IDENTICAL_NEIGHBORS
        and within_three_percentage >= NOISE_WITHIN_THREE_NEIGHBORS
    )


def should_remove_alpha_fringe(transparency_analysis: dict) -> bool:
    """Detecta imagens transparentes formadas quase inteiramente por pixels opacos."""
    return (
        transparency_analysis["transparent_pixels"] > 0
        and transparency_analysis["semitransparent_pixels"] > 0
        and transparency_analysis["near_opaque_percentage"]
        >= NEAR_OPAQUE_VISIBLE_PIXELS
    )


def remove_low_alpha_fringe(rgba_array: np.ndarray) -> tuple[np.ndarray, int]:
    """Torna invisiveis apenas os residuos com alfa muito baixo."""
    result = rgba_array.copy()
    alpha = result[:, :, 3]
    fringe_mask = (alpha > 0) & (alpha <= LOW_ALPHA_FRINGE_LIMIT)
    removed_pixels = int(np.count_nonzero(fringe_mask))
    result[fringe_mask] = (0, 0, 0, 0)
    return result, removed_pixels


def _find_repeated_detail_labels(
    rgba_array: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    centroids: np.ndarray,
    candidate_labels: list[int],
    area_limit: int,
) -> set[int]:
    """Protege pequenos componentes repetidos com cor e tamanho semelhantes."""
    minimum_area = max(
        MIN_ISOLATED_COMPONENT_AREA,
        round(area_limit * REPEATED_DETAIL_MIN_AREA_RATIO),
    )
    features = []

    for label in candidate_labels:
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < minimum_area:
            continue
        component_pixels = rgba_array[:, :, :3][labels == label]
        representative_rgb = np.median(component_pixels, axis=0).astype(np.uint8)
        representative_lab = cv2.cvtColor(
            representative_rgb.reshape(1, 1, 3).astype(np.float32) / 255.0,
            cv2.COLOR_RGB2LAB,
        )[0, 0]
        features.append((label, area, representative_lab, centroids[label]))

    protected_labels: set[int] = set()
    cluster_radius = min(rgba_array.shape[:2]) * REPEATED_DETAIL_CLUSTER_RATIO
    alignment_limit = max(
        2.0,
        min(rgba_array.shape[:2]) * REPEATED_DETAIL_ALIGNMENT_RATIO,
    )
    for _, reference_area, reference_lab, reference_center in features:
        matching_features = []
        for label, area, lab_color, center in features:
            area_difference = abs(area - reference_area) / max(area, reference_area)
            color_difference = float(np.linalg.norm(lab_color - reference_lab))
            spatial_distance = float(np.linalg.norm(center - reference_center))
            if (
                area_difference <= REPEATED_DETAIL_AREA_TOLERANCE
                and color_difference <= REPEATED_DETAIL_COLOR_DELTA_E
                and spatial_distance <= cluster_radius
            ):
                matching_features.append((label, center))
        if len(matching_features) < REPEATED_DETAIL_MIN_COUNT:
            continue

        points = np.array([center for _, center in matching_features])
        centered_points = points - np.mean(points, axis=0)
        _, _, directions = np.linalg.svd(centered_points, full_matrices=False)
        primary_direction = directions[0]
        raw_projections = centered_points @ primary_direction
        perpendicular = centered_points - np.outer(
            raw_projections,
            primary_direction,
        )
        if float(np.max(np.linalg.norm(perpendicular, axis=1))) > alignment_limit:
            continue

        spacings = np.diff(np.sort(raw_projections))
        positive_spacings = np.abs(spacings[np.abs(spacings) > 1e-6])
        if positive_spacings.size < REPEATED_DETAIL_MIN_COUNT - 1:
            continue
        if float(np.max(positive_spacings) / np.min(positive_spacings)) > (
            REPEATED_DETAIL_SPACING_RATIO
        ):
            continue
        protected_labels.update(label for label, _ in matching_features)

    return protected_labels


def remove_isolated_background_speckles(
    rgba_array: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Remove regioes minimas afastadas de um objeto sobre fundo uniforme."""
    height, width = rgba_array.shape[:2]
    border = np.concatenate(
        (
            rgba_array[0, :, :],
            rgba_array[-1, :, :],
            rgba_array[:, 0, :],
            rgba_array[:, -1, :],
        ),
        axis=0,
    )

    report = {
        "applied": False,
        "removed_components": 0,
        "removed_pixels": 0,
        "removed_protrusions": 0,
        "removed_protrusion_pixels": 0,
        "protected_repeated_details": 0,
        "area_limit": max(
            MIN_ISOLATED_COMPONENT_AREA,
            round(height * width * ISOLATED_COMPONENT_AREA_RATIO),
        ),
        "background_rgb": None,
        "border_coverage": 0.0,
    }

    if np.count_nonzero(border[:, 3] == 255) < border.shape[0] * 0.99:
        return rgba_array.copy(), report

    background_rgb = np.median(border[:, :3], axis=0).round().astype(np.uint8)
    border_rgb = border[:, :3].astype(np.float32) / 255.0
    background_sample = background_rgb.reshape(1, 1, 3).astype(np.float32) / 255.0
    border_lab = cv2.cvtColor(border_rgb.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB)
    background_lab = cv2.cvtColor(background_sample, cv2.COLOR_RGB2LAB)[0, 0]
    border_distances = np.linalg.norm(
        border_lab[:, 0, :] - background_lab,
        axis=1,
    )
    border_coverage = float(
        np.mean(border_distances <= BACKGROUND_BORDER_DELTA_E) * 100.0
    )
    report["background_rgb"] = tuple(int(channel) for channel in background_rgb)
    report["border_coverage"] = border_coverage

    if border_coverage < BACKGROUND_MIN_BORDER_COVERAGE:
        return rgba_array.copy(), report

    rgb_array = rgba_array[:, :, :3].astype(np.float32) / 255.0
    lab_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2LAB)
    background_distances = np.linalg.norm(lab_array - background_lab, axis=2)
    foreground_mask = (
        (rgba_array[:, :, 3] > LOW_ALPHA_FRINGE_LIMIT)
        & (background_distances > BACKGROUND_FOREGROUND_DELTA_E)
    ).astype(np.uint8)

    component_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        foreground_mask,
        connectivity=8,
    )
    if component_count <= 1:
        report["applied"] = True
        return rgba_array.copy(), report

    component_areas = stats[1:, cv2.CC_STAT_AREA]
    main_label = int(np.argmax(component_areas)) + 1
    main_area = int(stats[main_label, cv2.CC_STAT_AREA])
    if main_area < height * width * MAIN_COMPONENT_MIN_AREA_RATIO:
        return rgba_array.copy(), report

    main_mask = labels == main_label
    distance_to_main = cv2.distanceTransform(
        (~main_mask).astype(np.uint8),
        cv2.DIST_L2,
        5,
    )
    protected_distance = max(2.0, min(height, width) * NEAR_MAIN_PROTECTION_RATIO)
    candidate_labels: list[int] = []

    for label in range(1, component_count):
        if label == main_label:
            continue
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area > report["area_limit"]:
            continue
        component_mask = labels == label
        if float(np.min(distance_to_main[component_mask])) <= protected_distance:
            continue
        candidate_labels.append(label)

    protected_repeated_labels = _find_repeated_detail_labels(
        rgba_array,
        labels,
        stats,
        centroids,
        candidate_labels,
        report["area_limit"],
    )
    removable_labels = [
        label for label in candidate_labels if label not in protected_repeated_labels
    ]
    report["protected_repeated_details"] = len(protected_repeated_labels)

    result = rgba_array.copy()
    removal_mask = np.zeros((height, width), dtype=bool)
    if removable_labels:
        removal_mask = np.isin(labels, removable_labels)
        result[removal_mask, :3] = background_rgb
        result[removal_mask, 3] = 255
        report["removed_components"] = len(removable_labels)
        report["removed_pixels"] = int(np.count_nonzero(removal_mask))

    if len(removable_labels) >= NOISY_BACKGROUND_MIN_REMOVED_COMPONENTS:
        foreground_after_cleanup = foreground_mask.astype(bool) & ~removal_mask
        protected_repeated_mask = np.isin(labels, list(protected_repeated_labels))
        _, background_labels = cv2.connectedComponents(
            (~foreground_after_cleanup).astype(np.uint8),
            connectivity=8,
        )
        exterior_labels = np.unique(
            np.concatenate(
                (
                    background_labels[0, :],
                    background_labels[-1, :],
                    background_labels[:, 0],
                    background_labels[:, -1],
                )
            )
        )
        exterior_background = np.isin(
            background_labels,
            exterior_labels[exterior_labels != 0],
        )

        kernel_size = round(min(height, width) * SILHOUETTE_OPENING_RATIO)
        kernel_size = min(
            MAX_SILHOUETTE_KERNEL_SIZE,
            max(MIN_SILHOUETTE_KERNEL_SIZE, kernel_size),
        )
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (kernel_size, kernel_size),
        )
        opened_foreground = cv2.morphologyEx(
            foreground_after_cleanup.astype(np.uint8),
            cv2.MORPH_OPEN,
            kernel,
        )
        protrusion_mask = foreground_after_cleanup & ~opened_foreground.astype(bool)
        protrusion_count, protrusion_labels, protrusion_stats, _ = (
            cv2.connectedComponentsWithStats(
                protrusion_mask.astype(np.uint8),
                connectivity=8,
            )
        )
        removable_protrusions: list[int] = []
        adjacency_kernel = np.ones((3, 3), dtype=np.uint8)
        for protrusion_label in range(1, protrusion_count):
            area = int(protrusion_stats[protrusion_label, cv2.CC_STAT_AREA])
            if area < MIN_PROTRUSION_AREA or area > report["area_limit"]:
                continue
            component_mask = protrusion_labels == protrusion_label
            if np.any(component_mask & protected_repeated_mask):
                continue
            expanded_component = cv2.dilate(
                component_mask.astype(np.uint8),
                adjacency_kernel,
                iterations=1,
            ).astype(bool)
            if np.any(expanded_component & exterior_background):
                removable_protrusions.append(protrusion_label)

        if removable_protrusions:
            protrusion_removal_mask = np.isin(
                protrusion_labels,
                removable_protrusions,
            )
            result[protrusion_removal_mask, :3] = background_rgb
            result[protrusion_removal_mask, 3] = 255
            report["removed_protrusions"] = len(removable_protrusions)
            report["removed_protrusion_pixels"] = int(
                np.count_nonzero(protrusion_removal_mask)
            )

    report["applied"] = True
    return result, report


def choose_filter_speckle(
    transparency_analysis: dict,
    unique_colors: int,
    isolated_cleanup: dict | None = None,
) -> int:
    """Escolhe uma limpeza maior para franjas opacas grandes e fragmentadas."""
    has_protected_repeated_details = (
        isolated_cleanup is not None
        and isolated_cleanup.get("protected_repeated_details", 0) > 0
    )
    if has_protected_repeated_details:
        return DEFAULT_FILTER_SPECKLE

    has_detected_background_noise = (
        isolated_cleanup is not None
        and isolated_cleanup["applied"]
        and isolated_cleanup["removed_components"]
        >= NOISY_BACKGROUND_MIN_REMOVED_COMPONENTS
    )
    if has_detected_background_noise:
        return NOISY_BACKGROUND_FILTER_SPECKLE

    visible_pixels = (
        transparency_analysis["opaque_pixels"]
        + transparency_analysis["semitransparent_pixels"]
    )
    has_opaque_fringe_profile = (
        transparency_analysis["transparent_pixels"] > 0
        and transparency_analysis["semitransparent_pixels"] == 0
        and visible_pixels >= OPAQUE_FRINGE_MIN_VISIBLE_PIXELS
        and unique_colors >= OPAQUE_FRINGE_MIN_UNIQUE_COLORS
    )
    if has_opaque_fringe_profile:
        return OPAQUE_FRINGE_FILTER_SPECKLE
    return DEFAULT_FILTER_SPECKLE


def apply_bilateral_filter(rgba_array: np.ndarray, color_delta_e: float) -> np.ndarray:
    """Suaviza variacoes locais em Lab enquanto preserva bordas fortes."""
    rgb_array = rgba_array[:, :, :3].astype(np.float32) / 255.0
    lab_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2LAB)
    filtered_lab = cv2.bilateralFilter(
        lab_array,
        d=BILATERAL_DIAMETER,
        sigmaColor=color_delta_e,
        sigmaSpace=BILATERAL_SPATIAL_SIGMA,
    )
    filtered_rgb = cv2.cvtColor(filtered_lab, cv2.COLOR_LAB2RGB)

    result = rgba_array.copy()
    result[:, :, :3] = np.clip(filtered_rgb * 255.0, 0, 255).round().astype(np.uint8)
    return result


def normalize_near_black_interiors(
    rgba_array: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Unifica tons quase pretos no interior sem alterar os pixels de borda."""
    result = rgba_array.copy()
    _, interior_mask = find_near_black_masks(result)
    interior_pixels = result[:, :, :3][interior_mask]

    if not interior_pixels.size:
        return result, {
            "changed_pixels": 0,
            "unique_colors_before": 0,
            "representative_rgb": None,
        }

    colors, color_counts = np.unique(interior_pixels, axis=0, return_counts=True)
    representative = colors[np.argmax(color_counts)]
    changed_pixels = np.any(interior_pixels != representative, axis=1)
    result[:, :, :3][interior_mask] = representative

    return result, {
        "changed_pixels": int(np.count_nonzero(changed_pixels)),
        "unique_colors_before": int(colors.shape[0]),
        "representative_rgb": tuple(int(channel) for channel in representative),
    }


def preprocess_colors(input_path: Path, output_path: Path) -> dict:
    """Suaviza variacoes locais e salva uma nova imagem sem alterar a original."""
    with Image.open(input_path) as image:
        rgba_image = ImageOps.exif_transpose(image).convert("RGBA")
        rgba_array = np.array(rgba_image, dtype=np.uint8)

    cleaned_array, isolated_cleanup = remove_isolated_background_speckles(
        rgba_array
    )
    cleaned_image = Image.fromarray(cleaned_array, mode="RGBA")
    neighbor_analysis = analyze_neighbor_differences(cleaned_image)
    transparency_analysis = analyze_transparency(cleaned_image)
    filter_delta_e = estimate_filter_delta_e(neighbor_analysis)
    filter_applied = should_apply_bilateral_filter(neighbor_analysis)
    alpha_fringe_removed = should_remove_alpha_fringe(transparency_analysis)

    if alpha_fringe_removed:
        working_array, removed_alpha_pixels = remove_low_alpha_fringe(cleaned_array)
    else:
        working_array = cleaned_array
        removed_alpha_pixels = 0

    if filter_applied:
        filtered_array = apply_bilateral_filter(working_array, filter_delta_e)
    else:
        filtered_array = working_array

    normalized_array, dark_normalization = normalize_near_black_interiors(
        filtered_array
    )

    visible_mask = rgba_array[:, :, 3] > 0
    original_pixels = rgba_array[:, :, :3][visible_mask]
    filtered_pixels = normalized_array[:, :, :3][visible_mask]
    changed_pixels = np.any(original_pixels != filtered_pixels, axis=1)
    original_unique_colors = int(np.unique(original_pixels, axis=0).shape[0])
    filter_speckle = choose_filter_speckle(
        transparency_analysis,
        original_unique_colors,
        isolated_cleanup,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(normalized_array, mode="RGBA").save(output_path)

    return {
        "filter_applied": filter_applied,
        "filter_delta_e": filter_delta_e,
        "isolated_cleanup": isolated_cleanup,
        "alpha_fringe_removed": alpha_fringe_removed,
        "removed_alpha_pixels": removed_alpha_pixels,
        "dark_normalization": dark_normalization,
        "filter_speckle": filter_speckle,
        "changed_pixels": int(np.count_nonzero(changed_pixels)),
        "original_unique_colors": original_unique_colors,
        "remaining_unique_colors": int(np.unique(filtered_pixels, axis=0).shape[0]),
    }


def preprocess_and_vectorize(input_path: Path, output_path: Path) -> Path:
    """Pre-processa em um arquivo temporario e gera somente o SVG final."""
    with TemporaryDirectory(prefix="raster2svg-") as temporary_directory:
        temporary_image = Path(temporary_directory) / "preprocessed.png"
        report = preprocess_colors(input_path, temporary_image)
        return vectorize_image(
            temporary_image,
            output_path,
            filter_speckle=report["filter_speckle"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa o pre-processamento experimental e gera um SVG."
    )
    parser.add_argument("input_image", type=Path, help="Imagem que sera processada")
    args = parser.parse_args()

    if not args.input_image.is_file():
        parser.error(f"Imagem nao encontrada: {args.input_image}")

    image_output = Path("outputs") / f"{args.input_image.stem}-preprocessed.png"
    svg_output = Path("outputs") / f"{args.input_image.stem}-preprocessed.svg"

    result = preprocess_colors(args.input_image, image_output)
    vectorize_image(
        image_output,
        svg_output,
        filter_speckle=result["filter_speckle"],
    )

    filter_status = "sim" if result["filter_applied"] else "nao"
    print(f"Filtro bilateral aplicado: {filter_status}")
    alpha_status = "sim" if result["alpha_fringe_removed"] else "nao"
    print(f"Franja de alfa removida: {alpha_status}")
    print(f"Pixels de alfa descartados: {result['removed_alpha_pixels']:,}")
    print(f"Limite adaptativo usado: Delta E {result['filter_delta_e']:.2f}")
    filter_passes = 1 if result["filter_applied"] else 0
    print(f"Passagens do filtro: {filter_passes}")
    isolated = result["isolated_cleanup"]
    isolated_status = "sim" if isolated["applied"] else "nao"
    print(f"Limpeza de fundo uniforme aplicada: {isolated_status}")
    print(
        "Fragmentos isolados removidos: "
        f"{isolated['removed_components']} "
        f"({isolated['removed_pixels']:,} pixels)"
    )
    print(
        "Detalhes repetidos protegidos: "
        f"{isolated['protected_repeated_details']}"
    )
    print(f"Limpeza minima de regioes: {result['filter_speckle']} pixels")
    print(f"Pixels alterados: {result['changed_pixels']:,}")
    print(
        f"Cores exatas: {result['original_unique_colors']:,} -> "
        f"{result['remaining_unique_colors']:,}"
    )
    dark = result["dark_normalization"]
    if dark["representative_rgb"] is not None:
        print(
            "Normalizacao escura: "
            f"{dark['unique_colors_before']:,} cores interiores -> 1 | "
            f"{dark['changed_pixels']:,} pixels alterados"
        )
    print(f"Imagem de comparacao: {image_output}")
    print(f"SVG experimental: {svg_output}")


if __name__ == "__main__":
    main()

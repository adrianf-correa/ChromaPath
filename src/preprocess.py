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


def choose_filter_speckle(
    transparency_analysis: dict,
    unique_colors: int,
) -> int:
    """Escolhe uma limpeza maior para franjas opacas grandes e fragmentadas."""
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

    neighbor_analysis = analyze_neighbor_differences(rgba_image)
    transparency_analysis = analyze_transparency(rgba_image)
    filter_delta_e = estimate_filter_delta_e(neighbor_analysis)
    filter_applied = should_apply_bilateral_filter(neighbor_analysis)
    alpha_fringe_removed = should_remove_alpha_fringe(transparency_analysis)

    if alpha_fringe_removed:
        working_array, removed_alpha_pixels = remove_low_alpha_fringe(rgba_array)
    else:
        working_array = rgba_array.copy()
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
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(normalized_array, mode="RGBA").save(output_path)

    return {
        "filter_applied": filter_applied,
        "filter_delta_e": filter_delta_e,
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

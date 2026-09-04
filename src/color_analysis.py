import argparse
from collections import Counter
from itertools import combinations
from math import dist
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


LAB_FAMILY_DELTA_E = 3.0
NEAR_BLACK_LIGHTNESS_LIMIT = 15.0
NEAR_BLACK_CHROMA_LIMIT = 8.0


def analyze_colors(input_path: Path, top_n: int = 10) -> dict:
    """Conta as cores RGB visiveis e retorna um resumo da imagem."""
    with Image.open(input_path) as image:
        rgba_image = ImageOps.exif_transpose(image).convert("RGBA")
        neighbor_analysis = analyze_neighbor_differences(rgba_image)
        dark_analysis = analyze_dark_regions(rgba_image)
        transparency_analysis = analyze_transparency(rgba_image)
        visible_pixels = (
            (red, green, blue)
            for red, green, blue, alpha in rgba_image.get_flattened_data()
            if alpha > 0
        )
        color_counts = Counter(visible_pixels)

    total_pixels = sum(color_counts.values())
    dominant_colors = [
        {
            "rgb": rgb,
            "lab": rgb_to_lab(rgb),
            "pixels": count,
            "percentage": count / total_pixels * 100,
        }
        for rgb, count in color_counts.most_common(top_n)
    ]
    closest_pairs = find_closest_color_pairs(dominant_colors)
    color_families = group_similar_colors(dominant_colors)

    return {
        "total_pixels": total_pixels,
        "unique_colors": len(color_counts),
        "dominant_colors": dominant_colors,
        "closest_pairs": closest_pairs,
        "color_families": color_families,
        "neighbor_analysis": neighbor_analysis,
        "dark_analysis": dark_analysis,
        "transparency_analysis": transparency_analysis,
    }


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"#{red:02X}{green:02X}{blue:02X}"


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Converte uma cor RGB para CIELAB usando OpenCV."""
    rgb_pixel = np.array([[rgb]], dtype=np.float32) / 255.0
    lab_pixel = cv2.cvtColor(rgb_pixel, cv2.COLOR_RGB2LAB)[0, 0]
    return tuple(float(channel) for channel in lab_pixel)


def analyze_neighbor_differences(image: Image.Image) -> dict:
    """Mede a diferenca perceptual entre pixels vizinhos visiveis."""
    rgba_array = np.asarray(image, dtype=np.uint8)
    rgb_array = rgba_array[:, :, :3].astype(np.float32) / 255.0
    alpha_array = rgba_array[:, :, 3]
    lab_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2LAB)

    delta_parts = []

    if image.width > 1:
        horizontal_delta = np.linalg.norm(
            lab_array[:, 1:] - lab_array[:, :-1], axis=2
        )
        horizontal_visible = (alpha_array[:, 1:] > 0) & (alpha_array[:, :-1] > 0)
        delta_parts.append(horizontal_delta[horizontal_visible])

    if image.height > 1:
        vertical_delta = np.linalg.norm(
            lab_array[1:, :] - lab_array[:-1, :], axis=2
        )
        vertical_visible = (alpha_array[1:, :] > 0) & (alpha_array[:-1, :] > 0)
        delta_parts.append(vertical_delta[vertical_visible])

    if not delta_parts:
        return {
            "compared_pairs": 0,
            "identical_percentage": 0.0,
            "within_one_percentage": 0.0,
            "within_three_percentage": 0.0,
            "positive_median": 0.0,
            "positive_percentile_75": 0.0,
            "positive_percentile_90": 0.0,
            "positive_percentile_95": 0.0,
        }

    neighbor_deltas = np.concatenate(delta_parts)
    positive_deltas = neighbor_deltas[neighbor_deltas > 0.01]

    if positive_deltas.size:
        positive_median = float(np.median(positive_deltas))
        positive_percentile_75 = float(np.percentile(positive_deltas, 75))
        positive_percentile_90 = float(np.percentile(positive_deltas, 90))
        positive_percentile_95 = float(np.percentile(positive_deltas, 95))
    else:
        positive_median = 0.0
        positive_percentile_75 = 0.0
        positive_percentile_90 = 0.0
        positive_percentile_95 = 0.0

    return {
        "compared_pairs": int(neighbor_deltas.size),
        "identical_percentage": float(np.mean(neighbor_deltas <= 0.01) * 100),
        "within_one_percentage": float(np.mean(neighbor_deltas <= 1.0) * 100),
        "within_three_percentage": float(np.mean(neighbor_deltas <= 3.0) * 100),
        "positive_median": positive_median,
        "positive_percentile_75": positive_percentile_75,
        "positive_percentile_90": positive_percentile_90,
        "positive_percentile_95": positive_percentile_95,
    }


def find_near_black_masks(
    rgba_array: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Retorna mascaras booleanas para a regiao quase preta e seu interior."""
    rgb_array = rgba_array[:, :, :3]
    alpha_array = rgba_array[:, :, 3]
    lab_array = cv2.cvtColor(rgb_array.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)

    lightness = lab_array[:, :, 0]
    chroma = np.linalg.norm(lab_array[:, :, 1:3], axis=2)
    near_black_mask = (
        (alpha_array > 0)
        & (lightness <= NEAR_BLACK_LIGHTNESS_LIMIT)
        & (chroma <= NEAR_BLACK_CHROMA_LIMIT)
    )

    kernel = np.ones((3, 3), dtype=np.uint8)
    interior_mask = cv2.erode(
        near_black_mask.astype(np.uint8),
        kernel,
        iterations=1,
    ).astype(bool)
    return near_black_mask, interior_mask


def analyze_dark_regions(image: Image.Image) -> dict:
    """Separa o interior quase preto das bordas escuras da imagem."""
    rgba_array = np.asarray(image, dtype=np.uint8)
    rgb_array = rgba_array[:, :, :3]
    alpha_array = rgba_array[:, :, 3]
    near_black_mask, interior_mask = find_near_black_masks(rgba_array)
    boundary_mask = near_black_mask & ~interior_mask

    near_black_pixels = rgb_array[near_black_mask]
    interior_pixels = rgb_array[interior_mask]
    visible_pixels = int(np.count_nonzero(alpha_array > 0))

    if interior_pixels.size:
        interior_colors, color_counts = np.unique(
            interior_pixels,
            axis=0,
            return_counts=True,
        )
        representative = interior_colors[np.argmax(color_counts)]
        representative_rgb = tuple(int(channel) for channel in representative)
    else:
        representative_rgb = None

    return {
        "near_black_pixels": int(near_black_pixels.shape[0]),
        "near_black_percentage": (
            float(near_black_pixels.shape[0] / visible_pixels * 100)
            if visible_pixels
            else 0.0
        ),
        "near_black_unique_colors": int(
            np.unique(near_black_pixels, axis=0).shape[0]
        ),
        "interior_pixels": int(interior_pixels.shape[0]),
        "interior_unique_colors": int(np.unique(interior_pixels, axis=0).shape[0]),
        "boundary_pixels": int(np.count_nonzero(boundary_mask)),
        "representative_rgb": representative_rgb,
    }


def analyze_transparency(image: Image.Image) -> dict:
    """Resume pixels transparentes, semitransparentes e opacos."""
    alpha = np.asarray(image, dtype=np.uint8)[:, :, 3]
    total_pixels = int(alpha.size)
    transparent_pixels = int(np.count_nonzero(alpha == 0))
    opaque_pixels = int(np.count_nonzero(alpha == 255))
    visible_alpha = alpha[alpha > 0]
    semitransparent_alpha = alpha[(alpha > 0) & (alpha < 255)]

    if visible_alpha.size:
        alpha_values, alpha_counts = np.unique(visible_alpha, return_counts=True)
        dominant_alpha_index = int(np.argmax(alpha_counts))
        dominant_alpha = int(alpha_values[dominant_alpha_index])
        dominant_alpha_percentage = float(
            alpha_counts[dominant_alpha_index] / visible_alpha.size * 100
        )
        near_opaque_percentage = float(
            np.mean(visible_alpha >= 240) * 100
        )
    else:
        dominant_alpha = 0
        dominant_alpha_percentage = 0.0
        near_opaque_percentage = 0.0

    alpha_ranges = {
        "1_to_31": int(np.count_nonzero((alpha >= 1) & (alpha <= 31))),
        "32_to_63": int(np.count_nonzero((alpha >= 32) & (alpha <= 63))),
        "64_to_127": int(np.count_nonzero((alpha >= 64) & (alpha <= 127))),
        "128_to_191": int(np.count_nonzero((alpha >= 128) & (alpha <= 191))),
        "192_to_254": int(np.count_nonzero((alpha >= 192) & (alpha <= 254))),
    }

    return {
        "total_pixels": total_pixels,
        "transparent_pixels": transparent_pixels,
        "opaque_pixels": opaque_pixels,
        "semitransparent_pixels": int(semitransparent_alpha.size),
        "semitransparent_percentage": float(
            semitransparent_alpha.size / total_pixels * 100
        ),
        "semitransparent_median_alpha": (
            float(np.median(semitransparent_alpha))
            if semitransparent_alpha.size
            else 0.0
        ),
        "dominant_alpha": dominant_alpha,
        "dominant_alpha_percentage": dominant_alpha_percentage,
        "near_opaque_percentage": near_opaque_percentage,
        "alpha_ranges": alpha_ranges,
    }


def find_closest_color_pairs(colors: list[dict], limit: int = 5) -> list[dict]:
    """Encontra os pares mais proximos usando distancia perceptual CIELAB."""
    pairs = []

    for first_color, second_color in combinations(colors, 2):
        pairs.append(
            {
                "first_rgb": first_color["rgb"],
                "second_rgb": second_color["rgb"],
                "rgb_distance": dist(first_color["rgb"], second_color["rgb"]),
                "delta_e": dist(first_color["lab"], second_color["lab"]),
            }
        )

    return sorted(pairs, key=lambda pair: pair["delta_e"])[:limit]


def group_similar_colors(
    colors: list[dict], max_delta_e: float = LAB_FAMILY_DELTA_E
) -> list[dict]:
    """Agrupa cores proximas sem permitir que a referencia da familia se desloque."""
    families = []

    for color in colors:
        nearest_family = min(
            families,
            key=lambda family: dist(color["lab"], family["representative_lab"]),
            default=None,
        )

        if nearest_family is None:
            delta_e_to_family = None
        else:
            delta_e_to_family = dist(
                color["lab"], nearest_family["representative_lab"]
            )

        if nearest_family is None or delta_e_to_family > max_delta_e:
            families.append(
                {
                    "representative_rgb": color["rgb"],
                    "representative_lab": color["lab"],
                    "members": [color["rgb"]],
                    "pixels": color["pixels"],
                    "percentage": color["percentage"],
                }
            )
        else:
            nearest_family["members"].append(color["rgb"])
            nearest_family["pixels"] += color["pixels"]
            nearest_family["percentage"] += color["percentage"]

    return families


def print_report(report: dict) -> None:
    """Exibe no terminal um relatorio simples retornado por analyze_colors."""
    print(f"Pixels visiveis: {report['total_pixels']:,}")
    print(f"Cores RGB exatas: {report['unique_colors']:,}")
    print("\nCores mais frequentes:")

    for position, color in enumerate(report["dominant_colors"], start=1):
        hex_color = rgb_to_hex(color["rgb"])
        print(
            f"{position:>2}. RGB {color['rgb']} | "
            f"HEX {hex_color} | "
            f"{color['pixels']:,} pixels | "
            f"{color['percentage']:.2f}%"
        )

    print("\nPares mais proximos entre as cores dominantes:")
    for pair in report["closest_pairs"]:
        first_hex = rgb_to_hex(pair["first_rgb"])
        second_hex = rgb_to_hex(pair["second_rgb"])
        print(
            f"{first_hex} e {second_hex} | "
            f"RGB: {pair['rgb_distance']:.2f} | "
            f"Delta E: {pair['delta_e']:.2f}"
        )

    merged_families = [
        family for family in report["color_families"] if len(family["members"]) > 1
    ]
    print(
        f"\nFamilias perceptuais com Delta E maximo "
        f"{LAB_FAMILY_DELTA_E:.1f}:"
    )
    for family in merged_families:
        representative_hex = rgb_to_hex(family["representative_rgb"])
        member_colors = ", ".join(rgb_to_hex(rgb) for rgb in family["members"])
        print(
            f"{representative_hex} <- {member_colors} | "
            f"{family['pixels']:,} pixels | {family['percentage']:.2f}%"
        )

    neighbors = report["neighbor_analysis"]
    print("\nVariacao local entre pixels vizinhos:")
    print(f"Pares comparados: {neighbors['compared_pairs']:,}")
    print(f"Identicos (Delta E <= 0.01): {neighbors['identical_percentage']:.2f}%")
    print(f"Muito proximos (Delta E <= 1): {neighbors['within_one_percentage']:.2f}%")
    print(f"Proximos (Delta E <= 3): {neighbors['within_three_percentage']:.2f}%")
    print("Entre as diferencas maiores que zero:")
    print(f"  Mediana: {neighbors['positive_median']:.2f}")
    print(f"  Percentil 75: {neighbors['positive_percentile_75']:.2f}")
    print(f"  Percentil 90: {neighbors['positive_percentile_90']:.2f}")
    print(f"  Percentil 95: {neighbors['positive_percentile_95']:.2f}")

    dark = report["dark_analysis"]
    print("\nRegioes quase pretas e neutras:")
    print(
        f"Pixels detectados: {dark['near_black_pixels']:,} "
        f"({dark['near_black_percentage']:.2f}%)"
    )
    print(f"Cores exatas nessa faixa: {dark['near_black_unique_colors']:,}")
    print(f"Pixels interiores: {dark['interior_pixels']:,}")
    print(f"Cores exatas no interior: {dark['interior_unique_colors']:,}")
    print(f"Pixels de borda preservados: {dark['boundary_pixels']:,}")
    if dark["representative_rgb"] is not None:
        print(
            "Cor interior mais frequente: "
            f"{rgb_to_hex(dark['representative_rgb'])}"
        )

    transparency = report["transparency_analysis"]
    ranges = transparency["alpha_ranges"]
    print("\nTransparencia:")
    print(f"Totalmente transparentes: {transparency['transparent_pixels']:,}")
    print(f"Semitransparentes: {transparency['semitransparent_pixels']:,}")
    print(f"Totalmente opacos: {transparency['opaque_pixels']:,}")
    print(
        "Percentual semitransparente no quadro: "
        f"{transparency['semitransparent_percentage']:.2f}%"
    )
    print(
        "Alfa mediano entre os semitransparentes: "
        f"{transparency['semitransparent_median_alpha']:.1f}"
    )
    print(
        "Alfa mais frequente entre os visiveis: "
        f"{transparency['dominant_alpha']} "
        f"({transparency['dominant_alpha_percentage']:.2f}%)"
    )
    print(
        "Pixels visiveis quase opacos (alfa >= 240): "
        f"{transparency['near_opaque_percentage']:.2f}%"
    )
    print(
        "Faixas de alfa: "
        f"1-31: {ranges['1_to_31']:,} | "
        f"32-63: {ranges['32_to_63']:,} | "
        f"64-127: {ranges['64_to_127']:,} | "
        f"128-191: {ranges['128_to_191']:,} | "
        f"192-254: {ranges['192_to_254']:,}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisa as cores exatas de uma imagem.")
    parser.add_argument("input_image", type=Path, help="Imagem que sera analisada")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Quantidade de cores dominantes exibidas",
    )
    args = parser.parse_args()
    if args.top < 2:
        parser.error("--top precisa ser pelo menos 2")

    if not args.input_image.is_file():
        parser.error(f"Imagem nao encontrada: {args.input_image}")

    report = analyze_colors(args.input_image, top_n=args.top)
    print_report(report)


if __name__ == "__main__":
    main()

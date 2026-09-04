import argparse
from collections import Counter
from math import dist
from pathlib import Path
import re

from src.color_analysis import rgb_to_lab


SVG_FILL_PATTERN = re.compile(r'fill="(#[0-9A-Fa-f]{6})"')
SVG_COLOR_DELTA_E = 8.0
SVG_DARK_LIGHTNESS_LIMIT = 15.0


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converte uma cor hexadecimal do SVG para uma tupla RGB."""
    value = hex_color.removeprefix("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def build_color_mapping(
    fill_colors: list[str],
    max_delta_e: float = SVG_COLOR_DELTA_E,
) -> dict[str, str]:
    """Mapeia cores proximas para representantes sem limitar a paleta final."""
    color_counts = Counter(color.upper() for color in fill_colors)
    colors = [
        {
            "hex": hex_color,
            "lab": rgb_to_lab(hex_to_rgb(hex_color)),
            "paths": count,
        }
        for hex_color, count in color_counts.items()
    ]
    representatives = []
    mapping = {}

    dark_colors = [
        color
        for color in colors
        if color["lab"][0] <= SVG_DARK_LIGHTNESS_LIMIT
    ]
    if dark_colors:
        darkest_color = min(dark_colors, key=lambda color: color["lab"][0])
        for color in dark_colors:
            mapping[color["hex"]] = darkest_color["hex"]

    remaining_colors = sorted(
        (color for color in colors if color["hex"] not in mapping),
        key=lambda color: color["paths"],
        reverse=True,
    )

    for color in remaining_colors:
        hex_color = color["hex"]
        lab = color["lab"]
        nearest = min(
            representatives,
            key=lambda color: dist(lab, color["lab"]),
            default=None,
        )

        if nearest is None or dist(lab, nearest["lab"]) > max_delta_e:
            representatives.append(
                {
                    "hex": hex_color,
                    "lab": lab,
                    "paths": color["paths"],
                }
            )
            mapping[hex_color] = hex_color
        else:
            nearest["paths"] += color["paths"]
            mapping[hex_color] = nearest["hex"]

    return mapping


def simplify_svg_colors(
    svg: str,
    max_delta_e: float = SVG_COLOR_DELTA_E,
) -> tuple[str, dict]:
    """Unifica preenchimentos perceptualmente proximos e retorna um relatorio."""
    fill_colors = SVG_FILL_PATTERN.findall(svg)
    mapping = build_color_mapping(fill_colors, max_delta_e=max_delta_e)
    changed_paths = 0

    def replace_fill(match: re.Match) -> str:
        nonlocal changed_paths
        original = match.group(1)
        replacement = mapping[original.upper()]
        if replacement != original.upper():
            changed_paths += 1
        return f'fill="{replacement}"'

    simplified_svg = SVG_FILL_PATTERN.sub(replace_fill, svg)
    return simplified_svg, {
        "colors_before": len(set(color.upper() for color in fill_colors)),
        "colors_after": len(set(mapping.values())),
        "changed_paths": changed_paths,
        "max_delta_e": max_delta_e,
    }


def simplify_svg_file(input_path: Path, output_path: Path) -> dict:
    """Simplifica as cores de um arquivo SVG sem alterar seus caminhos."""
    svg = input_path.read_text(encoding="utf-8")
    simplified_svg, report = simplify_svg_colors(svg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(simplified_svg, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simplifica cores proximas de um SVG sem alterar sua geometria."
    )
    parser.add_argument("input_svg", type=Path, help="SVG que sera simplificado")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Caminho de saida (padrao: outputs/<nome>-colors.svg)",
    )
    args = parser.parse_args()

    if not args.input_svg.is_file():
        parser.error(f"SVG nao encontrado: {args.input_svg}")

    output_path = args.output or Path("outputs") / f"{args.input_svg.stem}-colors.svg"
    report = simplify_svg_file(args.input_svg, output_path)

    print(f"Delta E maximo: {report['max_delta_e']:.1f}")
    print(
        f"Cores de preenchimento: {report['colors_before']} -> "
        f"{report['colors_after']}"
    )
    print(f"Caminhos recoloridos: {report['changed_paths']}")
    print(f"SVG experimental: {output_path}")


if __name__ == "__main__":
    main()

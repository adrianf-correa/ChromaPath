from math import dist
from pathlib import Path
import re

from src.color_analysis import rgb_to_lab


PATH_PATTERN = re.compile(r"<path\b", re.IGNORECASE)
FILL_PATTERN = re.compile(r'\bfill="(#[0-9A-Fa-f]{6})"')


def analyze_svg(input_path: Path) -> dict[str, int]:
    """Conta caminhos, cores de preenchimento e bytes de um SVG."""
    svg = input_path.read_text(encoding="utf-8")

    path_count = len(PATH_PATTERN.findall(svg))
    fill_colors = {
        color.upper()
        for color in FILL_PATTERN.findall(svg)
    }

    return {
        "paths": path_count,
        "colors": len(fill_colors),
        "bytes": input_path.stat().st_size,
    }


def find_nearest_fill_distances(input_path: Path) -> list[float]:
    """Calcula a distância perceptual até a cor mais próxima de cada preenchimento."""
    svg = input_path.read_text(encoding="utf-8")
    hex_colors = sorted(
        {color.upper() for color in FILL_PATTERN.findall(svg)}
    )

    lab_colors = []
    for hex_color in hex_colors:
        value = hex_color.removeprefix("#")
        rgb = tuple(
            int(value[index : index + 2], 16)
            for index in (0, 2, 4)
        )
        lab_colors.append(rgb_to_lab(rgb))

    if len(lab_colors) < 2:
        return []

    nearest_distances = []
    for position, color_lab in enumerate(lab_colors):
        other_colors = (
            other_lab
            for other_position, other_lab in enumerate(lab_colors)
            if other_position != position
        )
        nearest_distances.append(
            min(dist(color_lab, other_lab) for other_lab in other_colors)
        )

    return sorted(nearest_distances)

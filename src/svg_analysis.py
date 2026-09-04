from pathlib import Path
import re


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
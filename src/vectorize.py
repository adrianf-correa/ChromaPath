from pathlib import Path

from PIL import Image, ImageOps
import vtracer

from src.svg_postprocess import simplify_svg_colors


VTRACER_COLOR_PRECISION = 5
VTRACER_HIERARCHICAL_MODE = "stacked"
SHARP_CORNER_THRESHOLD = 45
VTRACER_FILTER_SPECKLE = 4


def preprocess_image(input_path: Path) -> Image.Image:
    """Abre a imagem e a transforma em um formato previsivel para o VTracer."""
    with Image.open(input_path) as image:
        oriented_image = ImageOps.exif_transpose(image)
        return oriented_image.convert("RGBA")


def vectorize_image(
    input_path: Path,
    output_path: Path,
    *,
    simplify_colors: bool = True,
    filter_speckle: int = VTRACER_FILTER_SPECKLE,
) -> Path:
    """Pre-processa uma imagem raster e grava o SVG gerado pelo VTracer."""
    image = preprocess_image(input_path)
    pixels = list(image.get_flattened_data())

    svg = vtracer.convert_pixels_to_svg(
        pixels,
        image.size,
        mode="spline",
        filter_speckle=filter_speckle,
        color_precision=VTRACER_COLOR_PRECISION,
        hierarchical=VTRACER_HIERARCHICAL_MODE,
        corner_threshold=SHARP_CORNER_THRESHOLD,
    )
    if simplify_colors:
        svg, _ = simplify_svg_colors(svg)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    return output_path

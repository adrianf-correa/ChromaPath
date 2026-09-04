from pathlib import Path

from PIL import Image, ImageDraw


WIDTH = 800
HEIGHT = 600
BACKGROUND = (255, 255, 255, 255)
NAVY = (8, 38, 82, 255)
CYAN = (42, 198, 224, 255)
CORAL = (255, 76, 76, 255)
YELLOW = (255, 190, 12, 255)
FIXTURES_DIRECTORY = Path(__file__).resolve().parents[1] / "samples" / "fixtures"


def draw_diamond(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int) -> None:
    draw.polygon(
        (
            (x, y - radius),
            (x + radius, y),
            (x, y + radius),
            (x - radius, y),
        ),
        fill=YELLOW,
    )


def create_badge() -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (170, 185, 630, 505),
        radius=105,
        fill=NAVY,
    )
    draw.rounded_rectangle(
        (198, 213, 602, 477),
        radius=82,
        fill=CYAN,
    )
    draw.ellipse((265, 292, 335, 362), fill=NAVY)
    draw.ellipse((465, 292, 535, 362), fill=NAVY)
    draw.ellipse((288, 313, 306, 331), fill=BACKGROUND)
    draw.ellipse((488, 313, 506, 331), fill=BACKGROUND)
    draw.polygon(
        ((367, 378), (417, 378), (392, 426), (432, 426), (372, 474), (390, 431), (350, 431)),
        fill=CORAL,
    )

    return image


def create_clean_fixture() -> Image.Image:
    image = create_badge()
    draw = ImageDraw.Draw(image)

    draw_diamond(draw, 360, 115, 4)
    draw_diamond(draw, 400, 115, 4)
    draw_diamond(draw, 440, 115, 4)
    return image


def create_unique_detail_fixture() -> Image.Image:
    image = create_badge()
    draw = ImageDraw.Draw(image)
    draw.polygon(
        (
            (400, 105),
            (402, 110),
            (407, 112),
            (403, 115),
            (404, 121),
            (399, 117),
            (394, 120),
            (396, 114),
            (392, 111),
            (398, 110),
        ),
        fill=CORAL,
    )
    return image


def create_noisy_fixture(clean_image: Image.Image) -> Image.Image:
    image = clean_image.copy()
    draw = ImageDraw.Draw(image)
    fragments = (
        (55, 70, 1, CORAL),
        (105, 145, 2, NAVY),
        (690, 82, 1, CYAN),
        (735, 160, 2, CORAL),
        (72, 285, 1, YELLOW),
        (718, 300, 2, NAVY),
        (90, 470, 1, CYAN),
        (700, 500, 1, CORAL),
        (145, 545, 2, YELLOW),
        (650, 555, 1, NAVY),
        (245, 65, 1, CYAN),
        (555, 72, 2, CORAL),
        (40, 390, 1, NAVY),
        (760, 410, 2, CYAN),
    )
    for x, y, radius, color in fragments:
        draw.rectangle((x - radius, y - radius, x + radius, y + radius), fill=color)
    return image


def main() -> None:
    FIXTURES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    clean = create_clean_fixture()
    noisy = create_noisy_fixture(clean)
    clean.save(FIXTURES_DIRECTORY / "detached-details-clean.png")
    noisy.save(FIXTURES_DIRECTORY / "detached-details-noisy.png")

    unique_clean = create_unique_detail_fixture()
    unique_noisy = create_noisy_fixture(unique_clean)
    unique_clean.save(FIXTURES_DIRECTORY / "unique-detail-clean.png")
    unique_noisy.save(FIXTURES_DIRECTORY / "unique-detail-noisy.png")


if __name__ == "__main__":
    main()

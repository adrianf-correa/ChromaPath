from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image, ImageDraw

from src.vectorize import vectorize_image
from tools.geometry_experiment import experimental_trace
from tools.geometry_fixtures import reference_svg


class GeometryControlTests(unittest.TestCase):
    def test_experimental_control_and_explicit_length_four_match_production(self):
        image = Image.new("RGBA", (64, 64), "white")
        ImageDraw.Draw(image).ellipse((8, 8, 55, 55), fill=(20, 61, 105, 255))
        with TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.png", Path(directory) / "output.svg"
            image.save(source)
            vectorize_image(source, target)
            control = target.read_text(encoding="utf-8")
        self.assertEqual(experimental_trace(image, 4, {}), control)
        self.assertEqual(experimental_trace(image, 4, {"length_threshold": 4.0}), control)

    def test_reference_phase_uses_input_pixel_units(self):
        self.assertIn('translate(1.0 1.0)', reference_svg("tips", 96, 0.5))
        self.assertIn('translate(0.25 0.25)', reference_svg("tips", 384, 0.5))


if __name__ == "__main__":
    unittest.main()

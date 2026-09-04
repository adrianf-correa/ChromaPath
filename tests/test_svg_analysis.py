from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.svg_analysis import analyze_svg, find_nearest_fill_distances


class TestSvgAnalysis(unittest.TestCase):
    def test_counts_paths_unique_colors_and_bytes(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path fill="#ff0000" d="M 0 0"/>'
            '<path fill="#FF0000" d="M 1 1"/>'
            '<path fill="#0000ff" d="M 2 2"/>'
            "</svg>"
        )

        with TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "sample.svg"
            input_path.write_bytes(svg.encode("utf-8"))

            report = analyze_svg(input_path)

        self.assertEqual(report["paths"], 3)
        self.assertEqual(report["colors"], 2)
        self.assertEqual(report["bytes"], len(svg.encode("utf-8")))

    def test_calculates_distance_for_each_unique_fill_color(self) -> None:
        svg = (
            '<svg><path fill="#FF0000"/><path fill="#ff0000"/>'
            '<path fill="#0000FF"/></svg>'
        )

        with TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "sample.svg"
            input_path.write_bytes(svg.encode("utf-8"))

            distances = find_nearest_fill_distances(input_path)

        self.assertEqual(len(distances), 2)
        self.assertGreater(distances[0], 0.0)
        self.assertAlmostEqual(distances[0], distances[1])


if __name__ == "__main__":
    unittest.main()

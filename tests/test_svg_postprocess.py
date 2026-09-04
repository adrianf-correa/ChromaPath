import unittest

from src.svg_postprocess import build_color_mapping, simplify_svg_colors


class SvgColorSimplificationTests(unittest.TestCase):
    def test_merges_close_colors_and_preserves_distant_colors(self) -> None:
        colors = ["#101010", "#121212", "#FF0000", "#0000FF"]

        mapping = build_color_mapping(colors)

        self.assertEqual(mapping["#121212"], "#101010")
        self.assertNotEqual(mapping["#FF0000"], mapping["#0000FF"])

    def test_simplification_does_not_change_path_count(self) -> None:
        svg = (
            '<svg><path fill="#101010"/><path fill="#121212"/>'
            '<path fill="#FF0000"/></svg>'
        )

        result, report = simplify_svg_colors(svg)

        self.assertEqual(result.count("<path"), 3)
        self.assertEqual(report["colors_before"], 3)
        self.assertEqual(report["colors_after"], 2)

    def test_maps_very_dark_reddish_fill_to_darkest_fill(self) -> None:
        colors = ["#060505", "#3C0303", "#F9372F"]

        mapping = build_color_mapping(colors)

        self.assertEqual(mapping["#3C0303"], "#060505")
        self.assertEqual(mapping["#F9372F"], "#F9372F")

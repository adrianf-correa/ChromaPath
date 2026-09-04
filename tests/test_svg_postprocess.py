import unittest

from src.svg_postprocess import (
    build_color_mapping,
    choose_stable_threshold,
    simplify_svg_colors,
)


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
        self.assertEqual(report["max_delta_e"], 1.0)

    def test_maps_very_dark_reddish_fill_to_darkest_fill(self) -> None:
        colors = ["#060505", "#3C0303", "#F9372F"]

        mapping = build_color_mapping(colors)

        self.assertEqual(mapping["#3C0303"], "#060505")
        self.assertEqual(mapping["#F9372F"], "#F9372F")

    def test_chooses_beginning_of_reference_plateau(self) -> None:
        color_counts = [6, 5, 5, 5, 5, 4, 4, 4, 3, 3, 3, 3]
        reports = [
            {
                "max_delta_e": float(threshold),
                "colors_after": colors,
            }
            for threshold, colors in enumerate(color_counts, start=1)
        ]

        result = choose_stable_threshold(reports)

        self.assertEqual(result, 6.0)

    def test_chooses_lowest_threshold_when_all_are_stable(self) -> None:
        reports = [
            {
                "max_delta_e": float(threshold),
                "colors_after": 5,
            }
            for threshold in range(1, 13)
        ]

        result = choose_stable_threshold(reports)

        self.assertEqual(result, 1.0)

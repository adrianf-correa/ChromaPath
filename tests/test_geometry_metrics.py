import unittest

import numpy as np

from tools.geometry_metrics import geometry_metrics, mask_metrics, palette_labels, path_complexity


class GeometryMetricTests(unittest.TestCase):
    def test_counts_implicit_segments_and_exponents_not_letters(self):
        svg = '<svg><path d="M1e-3 2 3 4 L5 6 7 8 C1 2 3 4 5 6 7 8 9 10 11 12 Z"/></svg>'
        self.assertEqual(path_complexity(svg), dict(subpaths=1, line_segments=3,
                                                   cubic_segments=2, closes=1, segments=5))

    def test_unsupported_or_incomplete_commands_fail_loudly(self):
        for data in ("M0 0 H5", "M0 0 C1 2 3", "M0 0 Z1", "M0 0 @", "M"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                path_complexity(f'<svg><path d="{data}"/></svg>')

    def test_identical_masks_have_zero_error(self):
        mask = np.zeros((32, 32), bool)
        mask[8:24, 8:24] = True
        metrics = mask_metrics(mask, mask, 4)
        self.assertEqual(metrics["boundary_max_px"], 0)
        self.assertEqual(metrics["xor_area_px"], 0)

    def test_translation_is_measured_in_input_pixels(self):
        mask = np.zeros((64, 64), bool)
        mask[16:48, 16:48] = True
        metrics = mask_metrics(mask, np.roll(mask, 4, axis=1), 4)
        self.assertEqual(metrics["boundary_max_px"], 1)
        self.assertGreater(metrics["boundary_mean_px"], 0)

    def test_missing_detail_is_not_reported_as_zero_error(self):
        ref = np.zeros((32, 32), np.uint8)
        ref[10:13, 10:13] = 2
        metrics = geometry_metrics(ref, np.zeros_like(ref), 1)
        self.assertTrue(metrics["regions"]["2"]["missing_region"])
        self.assertIsNone(metrics["regions"]["2"]["boundary_max_px"])
        self.assertEqual(metrics["uncovered_area_px"], 9)

    def test_gap_between_colors_is_detected(self):
        ref = np.ones((20, 20), np.uint8)
        ref[:, 10:] = 2
        actual = ref.copy()
        actual[:, 10] = 0
        self.assertEqual(geometry_metrics(ref, actual, 1)["uncovered_area_px"], 20)

    def test_small_lost_tip_has_large_local_error_despite_large_body(self):
        ref = np.zeros((128, 128), bool)
        ref[30:120, 10:120] = True
        ref[20:30, 60:63] = True
        actual = ref.copy()
        actual[20:30] = False
        metrics = mask_metrics(ref, actual)
        self.assertLess(metrics["xor_area_px"] / ref.sum(), 0.004)
        self.assertEqual(metrics["boundary_max_px"], 10)

    def test_empty_masks_and_shape_errors(self):
        empty = np.zeros((8, 8), bool)
        self.assertEqual(mask_metrics(empty, empty)["boundary_max_px"], 0)
        with self.assertRaises(ValueError):
            mask_metrics(empty, empty[:4])

    def test_classification_tolerates_small_color_changes(self):
        rgb = np.array([[[254, 254, 254], [21, 60, 104]]], dtype=np.uint8)
        labels = palette_labels(rgb, ((255, 255, 255), (20, 61, 105)))
        np.testing.assert_array_equal(labels, [[0, 1]])

    def test_antialias_of_two_colors_does_not_invent_third_region(self):
        palette = ((255, 255, 255), (20, 61, 105), (239, 101, 72))
        weights = np.linspace(0, 1, 101)[:, None]
        rgb = ((1 - weights) * np.array(palette[0]) + weights * np.array(palette[1]))[None]
        labels = palette_labels(rgb.astype(np.uint8), palette)
        self.assertNotIn(2, labels)
        self.assertEqual(labels[0, 0], 0)
        self.assertEqual(labels[0, -1], 1)


if __name__ == "__main__":
    unittest.main()

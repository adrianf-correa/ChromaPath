import unittest

import numpy as np

from tools.edge_mixture import snap_exterior_mixtures
from tools.fringe_experiment import fringe_metrics


class FringeMetricTests(unittest.TestCase):
    def test_foreign_stripe_area_and_length_use_input_pixels(self):
        labels = np.zeros((192, 192), np.uint8)
        labels[30:162, 21] = 2
        expected = fringe_metrics(labels, 192, 0, 1)
        self.assertEqual(expected["left"], dict(foreign_area_px=132, affected_length_px=132))
        enlarged = np.repeat(np.repeat(labels, 4, axis=0), 4, axis=1)
        self.assertEqual(fringe_metrics(enlarged, 192, 0, 4), expected)

    def test_internal_color_and_white_gap_are_not_foreign_fringe(self):
        labels = np.ones((192, 192), np.uint8)
        labels[:, 100:] = 2  # coral legítimo no lado direito
        labels[30:162, 21] = 0  # fresta deve ser medida separadamente
        metrics = fringe_metrics(labels, 192, 0, 1)
        self.assertTrue(all(row["foreign_area_px"] == 0 for row in metrics.values()))

    def test_incompatible_grid_is_rejected(self):
        with self.assertRaises(ValueError):
            fringe_metrics(np.zeros((96, 96), np.uint8), 192, 0, 1)


class ExteriorMixtureCandidateTests(unittest.TestCase):
    def create_sample(self):
        image = np.full((40, 40, 4), 255, np.uint8)
        image[8:32, 8:32, :3] = (20, 60, 100)
        return image

    def test_crisp_colors_are_unchanged(self):
        image = self.create_sample()
        result, count = snap_exterior_mixtures(image)
        np.testing.assert_array_equal(result, image)
        self.assertEqual(count, 0)

    def test_mixture_is_changed_without_mutating_input(self):
        image = self.create_sample()
        image[8:32, 7, :3] = (137, 157, 177)
        original = image.copy()
        result, count = snap_exterior_mixtures(image)
        self.assertGreater(count, 0)
        self.assertTrue(np.any(result != image))
        np.testing.assert_array_equal(image, original)

    def test_transparent_or_nonuniform_border_is_not_processed(self):
        for channel in (0, 3):
            image = self.create_sample()
            image[0, 0, channel] = 0
            result, count = snap_exterior_mixtures(image)
            self.assertEqual(count, 0)
            np.testing.assert_array_equal(result, image)


if __name__ == "__main__":
    unittest.main()

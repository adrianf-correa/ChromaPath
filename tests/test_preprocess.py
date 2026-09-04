import unittest

import numpy as np

from src.preprocess import (
    choose_filter_speckle,
    normalize_near_black_interiors,
    remove_low_alpha_fringe,
    should_apply_bilateral_filter,
)


class FilterDecisionTests(unittest.TestCase):
    def test_flat_image_skips_filter(self) -> None:
        analysis = {
            "identical_percentage": 92.72,
            "within_three_percentage": 96.64,
        }

        result = should_apply_bilateral_filter(analysis)

        self.assertFalse(result)

    def test_image_with_variation_uses_filter(self) -> None:
        analysis = {
            "identical_percentage": 55.44,
            "within_three_percentage": 98.20,
        }

        result = should_apply_bilateral_filter(analysis)

        self.assertTrue(result)

    def test_gradient_image_skips_filter(self) -> None:
        analysis = {
            "identical_percentage": 32.85,
            "within_three_percentage": 93.37,
        }

        result = should_apply_bilateral_filter(analysis)

        self.assertFalse(result)

    def test_normalizes_dark_interior_and_preserves_boundary(self) -> None:
        image = np.full((7, 7, 4), 255, dtype=np.uint8)

        image[1:6, 1:6, :3] = (8, 8, 8)
        image[2:5, 2:5, :3] = (0, 0, 0)
        image[3, 3, :3] = (5, 5, 5)

        result, report = normalize_near_black_interiors(image)

        self.assertEqual(tuple(result[3, 3, :3]), (0, 0, 0))
        self.assertEqual(tuple(result[1, 1, :3]), (8, 8, 8))
        self.assertEqual(report["changed_pixels"], 1)

    def test_removes_only_very_low_alpha_pixels(self) -> None:
        image = np.array(
            [
                [
                    (10, 20, 30, 31),
                    (10, 20, 30, 32),
                ]
            ],
            dtype=np.uint8,
        )

        result, removed_pixels = remove_low_alpha_fringe(image)

        self.assertEqual(tuple(result[0, 0]), (0, 0, 0, 0))
        self.assertEqual(tuple(result[0, 1]), (10, 20, 30, 32))
        self.assertEqual(removed_pixels, 1)

    def test_uses_stronger_speckle_filter_for_large_opaque_fringe(self) -> None:
        transparency = {
            "transparent_pixels": 170_000,
            "semitransparent_pixels": 0,
            "opaque_pixels": 180_000,
        }

        result = choose_filter_speckle(transparency, unique_colors=6_000)

        self.assertEqual(result, 16)

    def test_keeps_default_speckle_filter_for_small_image(self) -> None:
        transparency = {
            "transparent_pixels": 20_000,
            "semitransparent_pixels": 0,
            "opaque_pixels": 30_000,
        }

        result = choose_filter_speckle(transparency, unique_colors=6_000)

        self.assertEqual(result, 4)

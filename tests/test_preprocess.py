import unittest

import numpy as np

from src.preprocess import (
    choose_filter_speckle,
    normalize_near_black_interiors,
    remove_low_alpha_fringe,
    remove_isolated_background_speckles,
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

    def test_removes_tiny_isolated_regions_from_uniform_background(self) -> None:
        image = np.full((100, 100, 4), 255, dtype=np.uint8)
        image[30:70, 30:70, :3] = (20, 80, 160)
        image[5:7, 5:7, :3] = (220, 30, 30)

        result, report = remove_isolated_background_speckles(image)

        self.assertTrue(report["applied"])
        self.assertEqual(report["removed_components"], 1)
        self.assertEqual(report["removed_pixels"], 4)
        self.assertEqual(tuple(result[5, 5]), (255, 255, 255, 255))
        self.assertEqual(tuple(result[30, 30]), (20, 80, 160, 255))

    def test_preserves_small_region_near_main_object(self) -> None:
        image = np.full((100, 100, 4), 255, dtype=np.uint8)
        image[30:70, 30:70, :3] = (20, 80, 160)
        image[48:50, 48:50, :3] = (240, 190, 20)

        result, report = remove_isolated_background_speckles(image)

        self.assertTrue(report["applied"])
        self.assertEqual(report["removed_components"], 0)
        self.assertEqual(tuple(result[48, 48]), (240, 190, 20, 255))

    def test_skips_isolated_cleanup_when_border_is_not_uniform(self) -> None:
        image = np.full((100, 100, 4), 255, dtype=np.uint8)
        image[0, ::2, :3] = (0, 0, 0)
        image[-1, ::2, :3] = (0, 0, 0)
        image[::2, 0, :3] = (0, 0, 0)
        image[::2, -1, :3] = (0, 0, 0)
        image[5:7, 5:7, :3] = (220, 30, 30)

        result, report = remove_isolated_background_speckles(image)

        self.assertFalse(report["applied"])
        self.assertEqual(report["removed_components"], 0)
        np.testing.assert_array_equal(result, image)

    def test_removes_small_protrusion_after_detecting_background_noise(self) -> None:
        image = np.full((100, 100, 4), 255, dtype=np.uint8)
        image[25:75, 25:75, :3] = (20, 80, 160)
        image[48:52, 75:78, :3] = (20, 80, 160)
        for index in range(8):
            row = 5 + index * 2
            image[row, 5:7, :3] = (220, 30, 30)

        result, report = remove_isolated_background_speckles(image)

        self.assertEqual(report["removed_components"], 8)
        self.assertGreaterEqual(report["removed_protrusions"], 1)
        self.assertEqual(tuple(result[49, 77]), (255, 255, 255, 255))

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

    def test_uses_stronger_filter_after_detecting_background_noise(self) -> None:
        transparency = {
            "transparent_pixels": 0,
            "semitransparent_pixels": 0,
            "opaque_pixels": 1_500_000,
        }
        isolated_cleanup = {
            "applied": True,
            "removed_components": 20,
        }

        result = choose_filter_speckle(
            transparency,
            unique_colors=50,
            isolated_cleanup=isolated_cleanup,
        )

        self.assertEqual(result, 32)

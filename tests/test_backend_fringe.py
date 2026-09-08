import unittest

import numpy as np

from tools.check_backend_fringe import assert_no_foreign_fringe


class BackendFringeAcceptanceTests(unittest.TestCase):
    def labels(self):
        labels = np.zeros((192, 192), dtype=np.uint8)
        labels[24:168, 24:96] = 1
        labels[24:168, 96:168] = 2
        return labels

    def test_valid_regions_without_external_coral_pass(self):
        assert_no_foreign_fringe(self.labels(), 192, 0, 1)

    def test_long_thin_fringe_fails_even_when_palette_is_unchanged(self):
        clean = self.labels()
        fringe = clean.copy()
        fringe[30:162, 21] = 2
        self.assertEqual(set(np.unique(clean)), set(np.unique(fringe)))
        with self.assertRaisesRegex(AssertionError, "132"):
            assert_no_foreign_fringe(fringe, 192, 0, 1)

    def test_blank_or_repainted_result_cannot_pass(self):
        for missing in (1, 2):
            labels = self.labels()
            labels[labels == missing] = 0
            with self.assertRaisesRegex(AssertionError, "missing"):
                assert_no_foreign_fringe(labels, 192, 0, 1)

    def test_single_oversampled_foreign_pixel_is_detected(self):
        labels = np.repeat(np.repeat(self.labels(), 4, axis=0), 4, axis=1)
        labels[160, 84] = 2
        with self.assertRaisesRegex(AssertionError, "0.0625"):
            assert_no_foreign_fringe(labels, 192, 0, 4)


if __name__ == "__main__":
    unittest.main()

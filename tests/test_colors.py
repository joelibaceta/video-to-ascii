"""Independent exhaustive reference for fixed ANSI palette selection."""
import unittest

import numpy as np

from video_to_ascii.colors import PALETTE, nearest_ansi


class ColorTests(unittest.TestCase):
    def test_nearest_ansi_matches_exhaustive_palette_search(self):
        rgb = np.random.default_rng(1).integers(0, 256, (2000, 3), dtype=np.int32)
        distances = ((rgb[:, None] - PALETTE[None, 16:].astype(np.int32)) ** 2).sum(axis=2)
        np.testing.assert_array_equal(nearest_ansi(rgb), distances.argmin(axis=1) + 16)

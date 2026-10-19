"""Documented luminance, density-ramp and fixed ANSI palette behavior."""
import unittest

import numpy as np

from video_to_ascii.colors import PALETTE, nearest_ansi
from video_to_ascii.render_strategy import image_processor
from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy
from video_to_ascii.render_strategy.ascii_color_filled_strategy import AsciiColorFilledStrategy


class RenderingContractTests(unittest.TestCase):
    def test_density_ramps_match_the_existing_upstream_code(self):
        self.assertEqual(image_processor.CHARS_LIGHT, list('  .:!+*e$@8'))
        self.assertEqual(image_processor.CHARS_COLOR, list('.*es◍'))
        self.assertEqual(image_processor.CHARS_FILLED, list('░▒▓█'))

    def test_green_contributes_most_and_blue_least(self):
        for grayscale in [False, True]:
            with self.subTest(grayscale=grayscale):
                red = image_processor.rgb_to_brightness(255, 0, 0, grayscale)
                green = image_processor.rgb_to_brightness(0, 255, 0, grayscale)
                blue = image_processor.rgb_to_brightness(0, 0, 255, grayscale)
                self.assertGreater(green, red)
                self.assertGreater(red, blue)
                self.assertAlmostEqual(red + green + blue, 255)

    def test_gray_ramp_uses_every_documented_density_threshold(self):
        gray = np.arange(256, dtype=np.uint8)
        frame = np.repeat(gray[None, :, None], 3, axis=2)
        for strategy, ramp in [(AsciiBWStrategy(), image_processor.CHARS_LIGHT),
                               (AsciiColorStrategy(), image_processor.CHARS_COLOR),
                               (AsciiColorFilledStrategy(), image_processor.CHARS_FILLED)]:
            with self.subTest(strategy=type(strategy).__name__):
                expected = np.array([ramp[int(value) * (len(ramp) - 1) // 255]
                                     for value in gray])
                actual = strategy.frame_to_cells(frame, (512, 2))[0][0]
                np.testing.assert_array_equal(actual, expected)

    def test_fixed_ansi_colors_map_back_to_their_own_indices(self):
        np.testing.assert_array_equal(nearest_ansi(PALETTE[16:]), np.arange(16, 256))

    def test_color_mapping_does_not_use_theme_dependent_entries(self):
        colors = np.random.default_rng(12).integers(0, 256, (4096, 3), dtype=np.uint8)
        mapped = nearest_ansi(colors)
        self.assertGreaterEqual(int(mapped.min()), 16)
        self.assertLessEqual(int(mapped.max()), 255)

"""Opt-in GPU checks: VIDEO_TO_ASCII_TEST_CUDA=1 python -m unittest discover -s tests."""
import os
import unittest

import cv2
import numpy as np

from video_to_ascii.colors import PALETTE, nearest_ansi
from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy
from video_to_ascii.render_strategy.ascii_color_filled_strategy import AsciiColorFilledStrategy


class ColorTests(unittest.TestCase):
    def test_nearest_ansi_matches_exhaustive_palette_search(self):
        rgb = np.random.default_rng(1).integers(0, 256, (2000, 3), dtype=np.int32)
        distances = ((rgb[:, None] - PALETTE[None, 16:].astype(np.int32)) ** 2).sum(axis=2)
        np.testing.assert_array_equal(nearest_ansi(rgb), distances.argmin(axis=1) + 16)


@unittest.skipUnless(os.environ.get('VIDEO_TO_ASCII_TEST_CUDA') == '1',
                     'Set VIDEO_TO_ASCII_TEST_CUDA=1 on an NVIDIA host')
class CudaTests(unittest.TestCase):
    def test_cpu_gpu_glyph_and_color_parity(self):
        from video_to_ascii.cuda_renderer import CudaCellMapper
        for cls in (AsciiColorStrategy, AsciiColorFilledStrategy, AsciiBWStrategy):
            with self.subTest(strategy=cls.__name__):
                frame = np.random.default_rng(42).integers(0, 256, (100, 256, 3), dtype=np.uint8)
                frame[0] = np.arange(256, dtype=np.uint8)[:, None]
                frame[1, :6] = np.array([[0, 0, 255], [0, 255, 0], [255, 0, 0],
                                         [95, 135, 175], [255, 255, 255], [0, 0, 0]])
                strategy = cls()
                reference = strategy.frame_to_cells(frame, (512, 101))
                actual = CudaCellMapper(strategy).frame_to_cells(frame)
                np.testing.assert_array_equal(actual[0], reference[0])
                if reference[1] is not None:
                    np.testing.assert_array_equal(actual[1], reference[1])

    def test_gpu_nv12_draws_glyphs_and_matches_cpu_luminance(self):
        from video_to_ascii.cuda_renderer import CudaCellMapper
        from video_to_ascii.mp4_export import CellRasterizer
        frame = np.random.default_rng(9).integers(0, 256, (12, 20, 3), dtype=np.uint8)
        strategy = AsciiColorStrategy()
        rasterizer = CellRasterizer((40, 15))
        mapper = CudaCellMapper(strategy)
        mapper.configure_raster(rasterizer)
        raw = np.frombuffer(mapper.render_nv12(frame), dtype=np.uint8)
        expected = rasterizer.width * rasterizer.height * 3 // 2
        self.assertEqual(raw.size, expected)
        cpu = rasterizer.render(*strategy.frame_to_cells(frame, (40, 15)))
        # Both paths use limited-range BT.601; integer rounding may differ by one.
        cpu_yuv = cv2.cvtColor(cpu, cv2.COLOR_RGB2YUV_I420)
        size = rasterizer.width * rasterizer.height
        error = np.abs(cpu_yuv.ravel()[:size].astype(int) - raw[:size].astype(int))
        self.assertLessEqual(error.max(), 1)
        self.assertGreater(raw[:size].max(), 30)
        self.assertGreater(np.count_nonzero(raw[:size] == 16), size // 2)

    def test_invalid_frame_buffers_are_rejected_before_kernel_launch(self):
        from video_to_ascii.cuda_renderer import CudaCellMapper
        mapper = CudaCellMapper(AsciiColorStrategy())
        for frame in [np.zeros((2, 2, 3), dtype=np.float32),
                      np.zeros((2, 2), dtype=np.uint8),
                      np.zeros((0, 2, 3), dtype=np.uint8)]:
            with self.subTest(shape=frame.shape, dtype=frame.dtype):
                with self.assertRaisesRegex(ValueError, 'uint8 BGR'):
                    mapper.frame_to_cells(frame)

    def test_odd_nv12_dimensions_are_rejected(self):
        from video_to_ascii.cuda_renderer import CudaCellMapper
        from video_to_ascii.mp4_export import CellRasterizer
        mapper = CudaCellMapper(AsciiColorStrategy())
        with self.assertRaisesRegex(ValueError, 'positive and even'):
            mapper.configure_raster(CellRasterizer((8, 4), (83, 65)))

    def test_cuda_mp4_pipeline_preserves_frame_count_and_resolution(self):
        import json
        from pathlib import Path
        import subprocess
        import tempfile
        from video_to_ascii.player import play
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            output = Path(folder) / 'ascii.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=256x256:rate=10', '-frames:v', '5',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
            play(str(source), output=str(output), backend='cuda', quality='lossless')
            streams = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]))['streams']
            video = next(s for s in streams if s['codec_type'] == 'video')
            self.assertEqual(int(video['nb_frames']), 5)
            self.assertEqual((video['width'], video['height']), (256, 256))
            decoded = cv2.VideoCapture(str(output))
            try:
                count = 0
                while decoded.read()[0]:
                    count += 1
                self.assertEqual(count, 5)
            finally:
                decoded.release()

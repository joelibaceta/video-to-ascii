"""The same rendering contract runs on CPU, CUDA and Metal implementations."""
import os
import unittest

import cv2
import numpy as np

from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy
from video_to_ascii.render_strategy.ascii_color_filled_strategy import AsciiColorFilledStrategy


class RendererContract:
    quality = 'standard'

    def test_cpu_gpu_glyph_and_color_parity(self):
        for cls in (AsciiColorStrategy, AsciiColorFilledStrategy, AsciiBWStrategy):
            with self.subTest(strategy=cls.__name__):
                frame = np.random.default_rng(42).integers(0, 256, (100, 256, 3), dtype=np.uint8)
                frame[0] = np.arange(256, dtype=np.uint8)[:, None]
                frame[1, :6] = np.array([[0, 0, 255], [0, 255, 0], [255, 0, 0],
                                         [95, 135, 175], [255, 255, 255], [0, 0, 0]])
                strategy = cls()
                reference = strategy.frame_to_cells(frame, (512, 101))
                actual = self.make_renderer(strategy).frame_to_cells(frame)
                np.testing.assert_array_equal(actual[0], reference[0])
                if reference[1] is not None:
                    np.testing.assert_array_equal(actual[1], reference[1])

    def test_raster_draws_glyphs_and_matches_cpu_luminance(self):
        from video_to_ascii.mp4_export import CellRasterizer
        frame = np.random.default_rng(9).integers(0, 256, (12, 20, 3), dtype=np.uint8)
        strategy = AsciiColorStrategy()
        rasterizer = CellRasterizer((40, 15))
        mapper = self.make_renderer(strategy)
        mapper.configure_raster(rasterizer)
        raw = np.frombuffer(mapper.render_frame(frame), dtype=np.uint8)
        cpu = rasterizer.render(*strategy.frame_to_cells(frame, (40, 15)))
        if mapper.pixel_format == 'rgb24':
            np.testing.assert_array_equal(raw.reshape(cpu.shape), cpu)
        else:
            expected = rasterizer.width * rasterizer.height * 3 // 2
            self.assertEqual(raw.size, expected)
            y = raw[:rasterizer.width*rasterizer.height].reshape(rasterizer.height, rasterizer.width)
            expected_y = cv2.cvtColor(cpu, cv2.COLOR_RGB2YUV_I420)[:rasterizer.height]
            np.testing.assert_allclose(y.astype(int), expected_y.astype(int), atol=1)

    def test_invalid_frame_buffers_are_rejected_before_kernel_launch(self):
        mapper = self.make_renderer(AsciiColorStrategy())
        for frame in [np.zeros((2, 2, 3), dtype=np.float32),
                      np.zeros((2, 2), dtype=np.uint8),
                      np.zeros((0, 2, 3), dtype=np.uint8)]:
            with self.subTest(shape=frame.shape, dtype=frame.dtype):
                with self.assertRaisesRegex(ValueError, 'uint8 BGR'):
                    mapper.frame_to_cells(frame)

    def test_odd_raster_dimensions_are_rejected(self):
        from video_to_ascii.mp4_export import CellRasterizer
        mapper = self.make_renderer(AsciiColorStrategy())
        with self.assertRaisesRegex(ValueError, 'positive and even'):
            mapper.configure_raster(CellRasterizer((8, 4), (83, 65)))

    def test_mp4_pipeline_preserves_frame_count_and_resolution(self):
        import json
        from pathlib import Path
        import subprocess
        import tempfile
        from video_to_ascii.player import play
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            output = Path(folder) / 'ascii.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=320x240:rate=10', '-frames:v', '5',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
            play(str(source), output=str(output), backend=self.backend, quality=self.quality)
            streams = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]))['streams']
            video = next(s for s in streams if s['codec_type'] == 'video')
            self.assertEqual(int(video['nb_frames']), 5)
            self.assertEqual((video['width'], video['height']), (320, 240))
            decoded = cv2.VideoCapture(str(output))
            try:
                count = 0
                while decoded.read()[0]:
                    count += 1
                self.assertEqual(count, 5)
            finally:
                decoded.release()


class CpuContract(RendererContract, unittest.TestCase):
    backend = 'cpu'

    def make_renderer(self, strategy):
        from video_to_ascii.backends.cpu import CpuRenderer
        return CpuRenderer(strategy)


@unittest.skipUnless(os.environ.get('VIDEO_TO_ASCII_TEST_CUDA') == '1',
                     'Set VIDEO_TO_ASCII_TEST_CUDA=1 on an NVIDIA host')
class CudaContract(RendererContract, unittest.TestCase):
    backend = 'cuda'
    quality = 'lossless'

    def make_renderer(self, strategy):
        from video_to_ascii.backends.cuda import CudaCellMapper
        return CudaCellMapper(strategy)


@unittest.skipUnless(os.environ.get('VIDEO_TO_ASCII_TEST_MLX') == '1',
                     'Set VIDEO_TO_ASCII_TEST_MLX=1 on an Apple Silicon Mac')
class MetalContract(RendererContract, unittest.TestCase):
    backend = 'metal'

    def make_renderer(self, strategy):
        from video_to_ascii.backends.metal import MlxCellMapper
        return MlxCellMapper(strategy)

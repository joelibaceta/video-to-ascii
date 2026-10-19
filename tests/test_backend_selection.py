"""Backend naming, optional imports and independent startup fallback policy."""
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from video_to_ascii.backends import backend_for, create_renderer, normalize_backend
from video_to_ascii.capture import open_capture
from video_to_ascii.mp4_export import CellRasterizer, select_encoder
from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy
from video_to_ascii.video_engine import VideoEngine


class BackendSelectionTests(unittest.TestCase):
    def test_mlx_alias_resolves_to_metal_without_changing_default(self):
        self.assertEqual(normalize_backend('mlx'), 'metal')
        self.assertEqual(VideoEngine(backend='mlx').backend, 'metal')
        self.assertEqual(VideoEngine().backend, 'cpu')

    def test_unknown_backend_is_rejected_at_engine_construction(self):
        with self.assertRaisesRegex(ValueError, 'Backend must be'):
            VideoEngine(backend='unknown')

    def test_auto_selects_platform_backend(self):
        with patch('video_to_ascii.backends.sys.platform', 'darwin'):
            self.assertEqual(backend_for('auto'), 'metal')
        with patch('video_to_ascii.backends.sys.platform', 'linux'):
            self.assertEqual(backend_for('auto'), 'cuda')

    def test_cpu_import_and_initialization_do_not_import_gpu_libraries(self):
        subprocess.run([sys.executable, '-c',
                        'import sys; from video_to_ascii.backends import create_renderer; '
                        'from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy; '
                        'assert create_renderer("cpu", AsciiColorStrategy()).name == "cpu"; '
                        'assert "cupy" not in sys.modules and "mlx.core" not in sys.modules; '
                        'assert "video_to_ascii.backends.cuda" not in sys.modules; '
                        'assert "video_to_ascii.backends.metal" not in sys.modules'], check=True)

    def test_explicit_gpu_initialization_failure_is_not_hidden(self):
        for name, module in [('cuda', 'backends.cuda.CudaCellMapper'),
                             ('metal', 'backends.metal.MlxCellMapper'),
                             ('mlx', 'backends.metal.MlxCellMapper')]:
            with self.subTest(backend=name), patch('video_to_ascii.' + module,
                                                  side_effect=ImportError('missing GPU library')):
                with self.assertRaisesRegex(RuntimeError, 'missing GPU library'):
                    create_renderer(name, AsciiColorStrategy())

    def test_auto_renderer_falls_back_for_either_platform(self):
        for target, module in [('cuda', 'backends.cuda.CudaCellMapper'),
                               ('metal', 'backends.metal.MlxCellMapper')]:
            with self.subTest(target=target), patch('video_to_ascii.backends.backend_for', return_value=target), patch(
                    'video_to_ascii.' + module, side_effect=RuntimeError('compile failed')):
                self.assertEqual(create_renderer('auto', AsciiColorStrategy()).name, 'cpu')

    def test_auto_raster_initialization_failure_falls_back_before_encoding(self):
        gpu = Mock()
        gpu.configure_raster.side_effect = RuntimeError('GPU allocation failed')
        rasterizer = CellRasterizer((40, 15))
        with patch('video_to_ascii.backends.backend_for', return_value='cuda'), patch(
                'video_to_ascii.backends.cuda.CudaCellMapper', return_value=gpu):
            renderer = create_renderer('auto', AsciiColorStrategy(), rasterizer)
        self.assertEqual(renderer.name, 'cpu')
        self.assertIs(renderer.rasterizer, rasterizer)

    def test_metal_decoder_failure_falls_back_only_for_auto(self):
        cpu = Mock()
        cpu.isOpened.return_value = True
        with patch('video_to_ascii.capture.backend_for', return_value='metal'), patch(
                'video_to_ascii.capture.AppleCapture', side_effect=RuntimeError('unsupported codec')), patch(
                'video_to_ascii.capture.cv2.VideoCapture', return_value=cpu):
            self.assertIs(open_capture('test.mov', 'auto', (40, 15)), cpu)
            for backend in ('metal', 'mlx'):
                with self.assertRaisesRegex(RuntimeError, 'METAL backend failed'):
                    open_capture('test.mov', backend, (40, 15))

    def test_encoder_failure_falls_back_only_for_auto(self):
        failed = Mock(returncode=1, stderr=b'encoder unavailable')
        with patch('video_to_ascii.mp4_export.subprocess.run', return_value=failed), patch(
                'video_to_ascii.mp4_export.backend_for', return_value='metal'):
            self.assertEqual(select_encoder('auto'), 'libx264')
            with self.assertRaisesRegex(RuntimeError, 'encoder unavailable'):
                select_encoder('metal')

    def test_explicit_cuda_probe_is_small_and_checks_lossless_options(self):
        with patch('video_to_ascii.mp4_export.subprocess.run', return_value=Mock(returncode=0)) as run:
            self.assertEqual(select_encoder('cuda', 'lossless', (640, 480)), 'h264_nvenc')
        command = run.call_args.args[0]
        self.assertIn('color=s=256x256', command)
        self.assertIn('lossless', command)
        self.assertIn('constqp', command)

    def test_auto_probe_preserves_output_size_validation_and_fallback(self):
        failed = Mock(returncode=1, stderr=b'unsupported dimensions')
        with patch('video_to_ascii.mp4_export.backend_for', return_value='cuda'), patch(
                'video_to_ascii.mp4_export.subprocess.run', return_value=failed) as run:
            self.assertEqual(select_encoder('auto', 'lossless', (640, 480)), 'libx264')
        command = run.call_args.args[0]
        self.assertIn('color=s=640x480', command)
        self.assertIn('lossless', command)

    def test_metal_lossless_uses_cpu_encoder_without_gpu_encoder_probe(self):
        with patch('video_to_ascii.mp4_export.subprocess.run') as run:
            self.assertEqual(select_encoder('metal', 'lossless'), 'libx264')
        run.assert_not_called()

    def test_missing_encoder_executable_has_clear_policy(self):
        with patch('video_to_ascii.mp4_export.subprocess.run', side_effect=FileNotFoundError('ffmpeg')):
            self.assertEqual(select_encoder('auto'), 'libx264')
            with self.assertRaisesRegex(RuntimeError, 'ffmpeg'):
                select_encoder('cuda')


class BackendImportTests(unittest.TestCase):
    def test_previous_cuda_import_resolves_to_same_implementation(self):
        from video_to_ascii.backends.cuda import CUDA_SOURCE, CudaCellMapper
        from video_to_ascii import cuda_renderer
        self.assertIs(cuda_renderer.CudaCellMapper, CudaCellMapper)
        self.assertIs(cuda_renderer.CUDA_SOURCE, CUDA_SOURCE)

    def test_previous_mlx_import_resolves_to_same_implementation(self):
        from video_to_ascii.backends.metal import MAP_SOURCE, RASTER_SOURCE, MlxCellMapper
        from video_to_ascii import mlx_renderer
        self.assertIs(mlx_renderer.MlxCellMapper, MlxCellMapper)
        self.assertIs(mlx_renderer.MAP_SOURCE, MAP_SOURCE)
        self.assertIs(mlx_renderer.RASTER_SOURCE, RASTER_SOURCE)

    def test_backend_modules_can_be_imported_without_gpu_libraries(self):
        subprocess.run([sys.executable, '-c',
                        'import sys; import video_to_ascii.backends.cpu; '
                        'import video_to_ascii.backends.cuda; '
                        'import video_to_ascii.backends.metal; '
                        'import video_to_ascii.cuda_renderer; '
                        'import video_to_ascii.mlx_renderer; '
                        'assert "cupy" not in sys.modules and "mlx.core" not in sys.modules'], check=True)

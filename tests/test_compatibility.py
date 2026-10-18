"""Keep existing callers and custom strategy implementations compatible."""
import inspect
import unittest
from unittest.mock import Mock, patch

from video_to_ascii.player import play
from video_to_ascii.video_engine import VideoEngine
from video_to_ascii import render_strategy


class CompatibilityTests(unittest.TestCase):
    def test_existing_calls_default_to_cpu(self):
        self.assertEqual(inspect.signature(play).parameters['backend'].default, 'cpu')
        self.assertEqual(VideoEngine().backend, 'cpu')

    def test_original_positional_player_arguments_still_bind(self):
        bound = inspect.signature(play).bind('input.mp4', 'ascii-color', None, None, False)
        self.assertEqual(bound.arguments['filename'], 'input.mp4')
        self.assertEqual(bound.arguments['play_audio'], False)

    def test_custom_strategy_can_require_constructor_arguments(self):
        class Custom:
            def __init__(self, value):
                self.value = value

        original = Custom('configured')
        with patch.dict(render_strategy.STRATEGIES, {'custom': original}):
            engine = VideoEngine(strategy='custom')
            self.assertEqual(engine.render_strategy.value, 'configured')

    def test_custom_renderer_receives_only_legacy_arguments(self):
        class Custom:
            def render(self, cap, output=None, output_format=None, with_audio=False):
                self.result = (cap, output, output_format, with_audio)

        with patch.dict(render_strategy.STRATEGIES, {'custom': Custom()}):
            engine = VideoEngine(strategy='custom', backend='cpu')
            engine.read_buffer = Mock()
            engine.play()
            self.assertEqual(engine.render_strategy.result,
                             (engine.read_buffer, None, None, False))
            engine.read_buffer.release.assert_called_once()

    def test_set_strategy_does_not_share_gpu_state_between_engines(self):
        one, two = VideoEngine(), VideoEngine()
        self.assertIsNot(one.render_strategy, two.render_strategy)
        one.render_strategy.cuda_mapper = object()
        self.assertFalse(hasattr(two.render_strategy, 'cuda_mapper'))

    def test_newline_flag_preserves_terminal_and_export_layouts(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
        strategy = AsciiBWStrategy()
        frame = np.full((3, 2, 3), 255, dtype=np.uint8)
        self.assertEqual(strategy.convert_frame_pixels_to_ascii(frame, (6, 4)),
                         '8888  ' * 3 + '\r\n')
        self.assertEqual(strategy.convert_frame_pixels_to_ascii(frame, (6, 4), True),
                         '8888\n' * 3)

    def test_custom_pixel_conversion_override_is_honored(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy

        class Custom(AsciiColorStrategy):
            def apply_pixel_to_ascii_strategy(self, pixel):
                return 'XX'

        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        self.assertEqual(Custom().convert_frame_pixels_to_ascii(frame, (4, 3), True),
                         'XXXX\nXXXX\n')

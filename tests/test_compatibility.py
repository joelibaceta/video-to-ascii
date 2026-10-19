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
        one.render_strategy.renderer = object()
        self.assertFalse(hasattr(two.render_strategy, 'renderer'))

    def test_existing_progress_bar_format_is_preserved(self):
        from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy
        self.assertEqual(AsciiColorStrategy().build_progress(5, 10),
                         '  |██████████░░░░░░░░░░| 50%')

    def test_newline_flag_preserves_terminal_and_export_layouts(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
        strategy = AsciiBWStrategy()
        frame = np.full((3, 2, 3), 255, dtype=np.uint8)
        self.assertEqual(strategy.convert_frame_pixels_to_ascii(frame, (6, 4)),
                         '@@@@  ' * 2 + '\r\n')
        self.assertEqual(strategy.convert_frame_pixels_to_ascii(frame, (6, 4), True),
                         '@@@@\n' * 2 + '\r\n')

    def test_custom_pixel_conversion_override_is_honored(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy

        class Custom(AsciiColorStrategy):
            def apply_pixel_to_ascii_strategy(self, pixel):
                return 'XX'

        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        self.assertEqual(Custom().convert_frame_pixels_to_ascii(frame, (4, 3), True),
                         'XXXX\n\r\n')


class LegacyCpuTests(unittest.TestCase):
    def test_cpu_play_does_not_select_a_new_renderer(self):
        with patch('video_to_ascii.video_engine.create_renderer') as create:
            engine = VideoEngine()
            engine.read_buffer = Mock()
            with patch.object(type(engine.render_strategy), 'render') as render:
                engine.play()
            create.assert_not_called()
            render.assert_called_once()
            self.assertFalse(hasattr(engine.render_strategy, 'renderer'))

    def test_cpu_capture_uses_existing_opencv_path(self):
        with patch('video_to_ascii.video_engine.cv2.VideoCapture') as capture, \
                patch('video_to_ascii.video_engine.open_capture') as accelerated:
            engine = VideoEngine()
            engine.load_video_from_file('input.mov')
            capture.assert_called_once_with('input.mov')
            accelerated.assert_not_called()

    def test_legacy_resize_is_height_based_even_for_narrow_terminal(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
        frame = np.zeros((10, 30, 3), dtype=np.uint8)
        self.assertEqual(AsciiBWStrategy().resize_frame(frame, (6, 5)).shape,
                         (5, 15, 3))

    def test_legacy_colorization_calls_original_pixel_converter(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy
        frame = np.array([[[12, 99, 231], [100, 0, 50]]] * 3, dtype=np.uint8)
        strategy = AsciiColorStrategy()
        row = ''.join(strategy.apply_pixel_to_ascii_strategy(p) for p in frame[0])
        self.assertEqual(strategy.convert_frame_pixels_to_ascii(frame, (4, 4), True),
                         (row + '\n') * 2 + '\r\n')

    def test_cell_mapping_does_not_switch_subsequent_legacy_calls(self):
        import numpy as np
        from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
        frame = np.full((3, 2, 3), 255, dtype=np.uint8)
        strategy = AsciiBWStrategy()
        before = strategy.convert_frame_pixels_to_ascii(frame, (4, 4), True)
        strategy.frame_to_cells(frame, (4, 4))
        self.assertEqual(strategy.convert_frame_pixels_to_ascii(frame, (4, 4), True), before)
        self.assertFalse(hasattr(strategy, 'renderer'))

    def test_new_sizing_options_explicitly_select_extended_renderer(self):
        with patch('video_to_ascii.video_engine.create_renderer') as create:
            engine = VideoEngine(columns=40, rows=15)
            engine.read_buffer = Mock()
            with patch.object(type(engine.render_strategy), 'render'):
                engine.play()
            create.assert_called_once_with('cpu', engine.render_strategy)

    def test_default_cpu_shell_export_preserves_upstream_format(self):
        import io
        import numpy as np
        from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
        cap = Mock()
        cap.get.return_value = 10
        cap.isOpened.return_value = True
        frame = np.full((2, 2, 3), 255, dtype=np.uint8)
        cap.read.side_effect = [(True, frame), (False, None)]
        output = io.StringIO()
        strategy = AsciiBWStrategy()
        with patch('builtins.open', return_value=output), \
                patch('os.popen') as terminal, patch('sys.stdout', new=io.StringIO()):
            terminal.return_value.read.return_value = '3 4'
            strategy.render(cap, output='legacy.sh', output_format='sh')
        script = output.getvalue()
        self.assertTrue(script.startswith("#!/bin/bash \n"))
        self.assertIn('sleep 0.033 \n', script)
        self.assertIn("echo -en '", script)
        self.assertNotIn('printf', script)

    def test_default_cpu_json_export_preserves_upstream_layout(self):
        import io
        import json
        import numpy as np
        from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
        cap = Mock()
        cap.get.return_value = 10
        cap.isOpened.return_value = True
        frame = np.full((2, 2, 3), 255, dtype=np.uint8)
        cap.read.side_effect = [(True, frame), (False, None)]
        output = io.StringIO()
        strategy = AsciiBWStrategy()
        with patch('builtins.open', return_value=output), \
                patch('os.popen') as terminal, patch('sys.stdout', new=io.StringIO()):
            terminal.return_value.read.return_value = '3 4'
            strategy.render(cap, output='legacy.json', output_format='json')
        self.assertEqual(json.loads(output.getvalue()), [['@@@@', '@@@@']])

"""Regression tests for headless export, shell replay, and backend selection."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from video_to_ascii.capture import open_capture
from video_to_ascii.player import play
from video_to_ascii.render_strategy.ascii_bw_strategy import AsciiBWStrategy
from video_to_ascii.render_strategy.ascii_color_strategy import AsciiColorStrategy


class VideoFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / 'test.avi'
        writer = cv2.VideoWriter(str(self.video), cv2.VideoWriter_fourcc(*'MJPG'), 10, (64, 48))
        self.assertTrue(writer.isOpened())
        for color in (0, 80, 255):
            writer.write(np.full((48, 64, 3), color, dtype=np.uint8))
        writer.release()

    def tearDown(self):
        self.temp.cleanup()


class ExportTests(VideoFixture):
    def test_shell_export_infers_format_and_replays(self):
        output = self.root / 'nested' / 'video.sh'
        play(str(self.video), output=str(output), backend='cpu', columns=40, rows=15)
        script = output.read_text()
        self.assertEqual(script.count('sleep 0.100000000'), 3)
        subprocess.run(['bash', '-n', str(output)], check=True)
        replay = subprocess.run(['bash', str(output)], capture_output=True, check=True)
        self.assertIn(b'\x1b[38;5;', replay.stdout)
        self.assertIn(b'\x1b[H', replay.stdout)

    def test_json_is_valid_and_obeys_frame_limit(self):
        output = self.root / 'video.json'
        play(str(self.video), strategy='just-ascii', output=str(output),
             backend='cpu', columns=40, rows=15, max_frames=2)
        frames = json.loads(output.read_text())
        self.assertEqual(len(frames), 2)
        self.assertTrue(all(len(line) <= 40 for frame in frames for line in frame))
        self.assertTrue(all(len(frame) <= 14 for frame in frames))

    def test_all_rows_and_black_white_brightness(self):
        frame = np.array([[[0, 0, 0], [255, 255, 255]]] * 3, dtype=np.uint8)
        self.assertEqual(AsciiBWStrategy().convert_frame_pixels_to_ascii(frame, (4, 4), True),
                         '  88\n' * 3)
        colored = AsciiColorStrategy().convert_frame_pixels_to_ascii(frame, (4, 4), True)
        self.assertEqual(len(colored.splitlines()), 3)
        self.assertIn('\033[38;5;16m', colored)

    def test_strict_cuda_does_not_silently_fallback(self):
        with patch('video_to_ascii.capture.CudaCapture', side_effect=RuntimeError('GPU unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'CUDA backend failed'):
                open_capture(str(self.video), 'cuda', (40, 15))
            cap = open_capture(str(self.video), 'auto', (40, 15))
            try:
                self.assertTrue(cap.read()[0])
            finally:
                cap.release()

    def test_mp4_contains_decodable_ascii_frames(self):
        output = self.root / 'video.mp4'
        play(str(self.video), output=str(output), backend='cpu',
             columns=40, rows=15, max_frames=2)
        probe = json.loads(subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]))
        video = probe['streams'][0]
        self.assertEqual(video['codec_name'], 'h264')
        self.assertEqual(int(video['nb_frames']), 2)
        self.assertAlmostEqual(float(video['duration']), 0.2, places=2)
        cap = cv2.VideoCapture(str(output))
        try:
            self.assertTrue(cap.read()[0])
            ok, frame = cap.read()
            self.assertTrue(ok)
            # Glyphs leave black background and lit foreground within each cell.
            self.assertGreater(frame.max(), 20)
            self.assertGreater(np.count_nonzero(frame < 10), frame.size // 2)
        finally:
            cap.release()

    def test_mp4_defaults_to_source_resolution(self):
        output = self.root / 'source_size.mp4'
        play(str(self.video), output=str(output), backend='cpu', max_frames=2,
             quality='lossless')
        probe = json.loads(subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]))
        video = probe['streams'][0]
        self.assertEqual((video['width'], video['height']), (64, 48))
        self.assertEqual(int(video['nb_frames']), 2)

    def test_invalid_output_fails_instead_of_creating_empty_file(self):
        with self.assertRaisesRegex(ValueError, '.sh or .json'):
            play(str(self.video), output=str(self.root / 'video.txt'), backend='cpu')
        self.assertFalse((self.root / 'video.txt').exists())

class Mp4SafetyTests(VideoFixture):
    """Validate audio and existing files independently of CUDA availability."""

    def test_lossless_export_copies_audio_packets(self):
        source = self.root / 'audio.mp4'
        output = self.root / 'audio-ascii.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=size=64x48:rate=10', '-f', 'lavfi', '-i',
                        'sine=frequency=440:sample_rate=48000', '-t', '0.3',
                        '-c:v', 'libx264', '-c:a', 'aac', str(source)], check=True)
        play(str(source), output=str(output), backend='cpu', quality='lossless')

        def audio_hashes(path):
            data = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-select_streams', 'a:0',
                '-show_packets', '-show_data_hash', 'sha256', '-of', 'json', str(path)]))
            return [packet['data_hash'] for packet in data['packets']]

        self.assertTrue(audio_hashes(source))
        self.assertEqual(audio_hashes(source), audio_hashes(output))

    def test_encoder_failure_preserves_existing_output(self):
        output = self.root / 'existing.mp4'
        output.write_bytes(b'existing output')
        with patch('video_to_ascii.mp4_export.select_encoder', return_value='invalid_encoder'):
            with self.assertRaises(RuntimeError):
                play(str(self.video), output=str(output), backend='cpu', max_frames=1)
        self.assertEqual(output.read_bytes(), b'existing output')

    def test_mp4_export_cannot_overwrite_source(self):
        original = self.video.read_bytes()
        with self.assertRaisesRegex(ValueError, 'must differ from input'):
            play(str(self.video), output=str(self.video), output_format='mp4', backend='cpu')
        self.assertEqual(self.video.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

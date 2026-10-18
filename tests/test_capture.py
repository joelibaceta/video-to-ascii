"""Capture error handling without requiring NVIDIA hardware."""
import io
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from video_to_ascii.capture import CudaCapture, open_capture
from video_to_ascii.mp4_export import select_encoder


class CaptureTests(unittest.TestCase):
    def capture(self, data, code=0):
        cap = CudaCapture.__new__(CudaCapture)
        cap.width, cap.height, cap.rotation = 2, 2, 0
        cap.errors = io.BytesIO(b'decoder failed')
        cap.process = Mock(stdout=io.BytesIO(data))
        cap.process.wait.return_value = code
        return cap

    def test_clean_eof_and_truncated_frame_are_distinct(self):
        self.assertIsNone(self.capture(b'')._read())
        with self.assertRaisesRegex(RuntimeError, 'decoder failed'):
            self.capture(b'partial')._read()

    def test_decoder_failure_at_frame_boundary_is_not_clean_eof(self):
        with self.assertRaisesRegex(RuntimeError, 'decoder failed'):
            self.capture(b'', code=1)._read()

    def test_display_rotation_preserves_pixel_positions(self):
        image = np.arange(12, dtype=np.uint8).reshape(2, 2, 3)
        cap = self.capture(image.tobytes())
        cap.rotation = 90
        np.testing.assert_array_equal(cap._read(), cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE))

    def test_cpu_backend_never_attempts_cuda(self):
        cpu = Mock()
        with patch('video_to_ascii.capture.CudaCapture') as gpu, patch(
                'video_to_ascii.capture.cv2.VideoCapture', return_value=cpu):
            self.assertIs(open_capture('input.mp4', 'cpu', (40, 15)), cpu)
            gpu.assert_not_called()

    def test_invalid_cpu_input_releases_capture(self):
        cpu = Mock()
        cpu.isOpened.return_value = False
        with patch('video_to_ascii.capture.cv2.VideoCapture', return_value=cpu):
            with self.assertRaisesRegex(RuntimeError, 'Cannot open video'):
                open_capture('missing.mp4', 'cpu', (40, 15))
        cpu.release.assert_called_once()

    def test_nvenc_failure_is_strict_only_when_requested(self):
        failed = Mock(returncode=1, stderr=b'encoder unavailable')
        with patch('video_to_ascii.mp4_export.subprocess.run', return_value=failed):
            with self.assertRaisesRegex(RuntimeError, 'encoder unavailable'):
                select_encoder(True, True)
            self.assertEqual(select_encoder(True, False), 'libx264')

    def test_unknown_frame_count_does_not_disable_cuda(self):
        import json
        metadata = dict(width=64, height=48, nb_frames='N/A',
                        avg_frame_rate='0/0', r_frame_rate='25/1', pix_fmt='yuv420p')
        probe = Mock(stdout=json.dumps({'streams': [metadata]}))
        with patch('video_to_ascii.capture.subprocess.run', return_value=probe), patch(
                'video_to_ascii.capture.subprocess.Popen') as popen, patch.object(
                CudaCapture, '_read', return_value=np.zeros((2, 2, 3), dtype=np.uint8)):
            popen.return_value.poll.return_value = 0
            cap = CudaCapture('input.mkv', (40, 15))
            try:
                self.assertEqual(cap.get(cv2.CAP_PROP_FRAME_COUNT), 0)
                self.assertEqual(cap.get(cv2.CAP_PROP_FPS), 25)
            finally:
                cap.release()

    def test_failed_process_start_closes_error_file(self):
        import json
        metadata = dict(width=64, height=48, nb_frames='2',
                        avg_frame_rate='10/1', pix_fmt='yuv420p')
        errors = io.BytesIO()
        with patch('video_to_ascii.capture.subprocess.run', return_value=Mock(
                stdout=json.dumps({'streams': [metadata]}))), patch(
                'video_to_ascii.capture.tempfile.TemporaryFile', return_value=errors), patch(
                'video_to_ascii.capture.subprocess.Popen', side_effect=FileNotFoundError('ffmpeg')):
            with self.assertRaises(FileNotFoundError):
                CudaCapture('input.mp4', (40, 15))
        self.assertTrue(errors.closed)

    def test_release_kills_a_decoder_that_does_not_terminate(self):
        import subprocess
        cap = self.capture(b'')
        cap.process.poll.return_value = None
        cap.process.wait.side_effect = [subprocess.TimeoutExpired('ffmpeg', 5), 0]
        cap.release()
        cap.process.terminate.assert_called_once()
        cap.process.kill.assert_called_once()
        self.assertTrue(cap.process.stdout.closed)
        self.assertTrue(cap.errors.closed)

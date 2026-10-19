"""FFmpeg hardware decoding with an OpenCV CPU fallback."""
import json
import subprocess
import tempfile
import sys
from fractions import Fraction

import cv2
import numpy as np

from .backends import backend_for, normalize_backend


class FFmpegCapture:
    name = 'FFmpeg'

    def __init__(self, filename, dimensions):
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_streams', '-of', 'json', filename],
            check=True, capture_output=True, text=True)
        stream = json.loads(probe.stdout)['streams'][0]
        rate = stream.get('avg_frame_rate', '0/0')
        if rate in ('0/0', '0'):
            rate = stream.get('r_frame_rate', '30/1')
        self.fps = float(Fraction(rate if rate not in ('0/0', '0') else '30/1')) or 30
        frame_count = str(stream.get('nb_frames') or '')
        self.frames = int(frame_count) if frame_count.isdecimal() else 0
        self.rotation = int(next((s.get('rotation', 0) for s in
                                stream.get('side_data_list', [])
                                if 'rotation' in s), stream.get('tags', {}).get('rotate', 0))) % 360
        cols, rows = dimensions
        width, height = stream['width'], stream['height']
        rotated = self.rotation in (90, 270)
        display_w, display_h = (height, width) if rotated else (width, height)
        scale = min((cols // 2) / display_w, (rows - 1) / display_h)
        self.width = max(2, int(width * scale) // 2 * 2)
        self.height = max(2, int(height * scale) // 2 * 2)
        pixel_format = 'p010le' if '10' in stream['pix_fmt'] else 'nv12'
        command = self._command(filename, pixel_format)
        self.errors = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                            stderr=self.errors)
        except OSError:
            self.errors.close()
            raise
        try:
            self.pending = self._read()
            if self.pending is None:
                raise RuntimeError(f'{self.name} decoder produced no frames')
        except BaseException:
            self.release()
            raise

    def _read(self):
        size = self.width * self.height * 3
        data = self.process.stdout.read(size)
        if len(data) != size:
            code = self.process.wait()
            if code or data:
                self.errors.seek(0)
                raise RuntimeError(self.errors.read().decode(errors='replace') or
                                   f'Incomplete {self.name} frame')
            return None
        frame = np.frombuffer(data, dtype=np.uint8).reshape(self.height, self.width, 3)
        rotations = {90: cv2.ROTATE_90_COUNTERCLOCKWISE,
                     180: cv2.ROTATE_180, 270: cv2.ROTATE_90_CLOCKWISE}
        return cv2.rotate(frame, rotations[self.rotation]) if self.rotation else frame

    def read(self):
        if self.pending is not None:
            frame, self.pending = self.pending, None
        else:
            frame = self._read()
        return frame is not None, frame

    def isOpened(self):
        return self.process.stdout is not None and not self.process.stdout.closed

    def get(self, prop):
        return {cv2.CAP_PROP_FPS: self.fps,
                cv2.CAP_PROP_FRAME_COUNT: self.frames}.get(prop, 0)

    def release(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.stdout.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.errors.close()


class CudaCapture(FFmpegCapture):
    name = 'CUDA'

    def _command(self, filename, pixel_format):
        return ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
             '-threads', '2', '-filter_threads', '1', '-filter_complex_threads', '1',
             '-noautorotate', '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda',
             '-i', filename, '-map', '0:v:0', '-an', '-sn',
             '-vf', f'scale_cuda={self.width}:{self.height}:interp_algo=bilinear,'
                    f'hwdownload,format={pixel_format},format=bgr24',
             '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1']


class AppleCapture(FFmpegCapture):
    """VideoToolbox decoding with host-side scaling and frame transfer."""
    name = 'VideoToolbox'

    def _command(self, filename, pixel_format):
        if sys.platform != 'darwin':
            raise RuntimeError('VideoToolbox requires macOS')
        return ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-threads', '2', '-filter_threads', '1', '-noautorotate',
                '-hwaccel', 'videotoolbox', '-i', filename, '-map', '0:v:0', '-an', '-sn',
                '-vf', f'scale={self.width}:{self.height}:flags=bilinear,format=bgr24',
                '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1']


def open_capture(filename, backend, dimensions):
    backend = normalize_backend(backend)
    target = backend_for(backend)
    if target != 'cpu':
        try:
            capture_class = AppleCapture if target == 'metal' else CudaCapture
            cap = capture_class(filename, dimensions)
            print(f'Decoder: {cap.name}', file=sys.stderr)
            return cap
        except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError, RuntimeError) as exc:
            if backend != 'auto':
                raise RuntimeError(f'{target.upper()} backend failed: {exc}') from exc
            print(f'GPU decoding unavailable; using CPU: {exc}', file=sys.stderr)
    cap = cv2.VideoCapture(filename)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f'Cannot open video: {filename}')
    print('Decoder: CPU (OpenCV)', file=sys.stderr)
    return cap

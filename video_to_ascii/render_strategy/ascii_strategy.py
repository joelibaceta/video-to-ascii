"""Render resized video frames as terminal text or replayable exports."""
import json
import shutil
import sys
import time
import wave
import tempfile
from pathlib import Path

import cv2
import numpy as np

from . import render_strategy as re
from . import image_processor as ipe
from ..colors import nearest_ansi

DEFAULT_TERMINAL_SIZE = tuple(shutil.get_terminal_size((120, 40)))


class AsciiStrategy(re.RenderStrategy):
    def _uses_builtin_pixel_conversion(self):
        from .ascii_bw_strategy import AsciiBWStrategy
        from .ascii_color_strategy import AsciiColorStrategy
        from .ascii_color_filled_strategy import AsciiColorFilledStrategy
        method = self.apply_pixel_to_ascii_strategy
        method = getattr(method, '__func__', method)
        return method in {
            AsciiStrategy.apply_pixel_to_ascii_strategy,
            AsciiBWStrategy.apply_pixel_to_ascii_strategy,
            AsciiColorStrategy.apply_pixel_to_ascii_strategy,
            AsciiColorFilledStrategy.apply_pixel_to_ascii_strategy,
        }

    def apply_pixel_to_ascii_strategy(self, pixel):
        return ipe.pixel_to_ascii(pixel)

    def frame_to_cells(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
        mapper = getattr(self, 'cuda_mapper', None)
        if mapper is not None:
            return mapper.frame_to_cells(frame[:, :dimensions[0] // 2])
        # Do color math in arrays, then assemble text from a small lookup table.
        from .ascii_bw_strategy import AsciiBWStrategy
        from .ascii_color_filled_strategy import AsciiColorFilledStrategy
        colored = not isinstance(self, AsciiBWStrategy)
        density = 2 if isinstance(self, AsciiColorFilledStrategy) else (1 if colored else 0)
        rgb = frame[:, :dimensions[0] // 2, ::-1].astype(np.float64)
        weights = [0.267, 0.642, 0.091] if colored else [0.2126, 0.7152, 0.0722]
        brightness = rgb @ np.array(weights)
        chars = np.array(ipe.DENSITY[density])
        indices = np.clip((brightness * (len(chars) - 1) / 255 + 1e-12).astype(int), 0, len(chars) - 1)
        glyphs = chars[indices]
        if colored:
            high = rgb.max(axis=2, keepdims=True)
            low = rgb.min(axis=2, keepdims=True)
            saturation = np.divide(high - low, high, out=np.zeros_like(high), where=high != 0)
            boosted = np.minimum(saturation + 0.3, 1)
            ratio = np.divide(boosted, saturation, out=np.ones_like(high), where=saturation != 0)
            rgb = np.clip(high - (high - rgb) * ratio, 0, 255).astype(int)
            ansi = nearest_ansi(rgb)
        else:
            ansi = None
        return glyphs, ansi

    def convert_frame_pixels_to_ascii(self, frame, dimensions=DEFAULT_TERMINAL_SIZE,
                                      new_line_chars=False):
        if not self._uses_builtin_pixel_conversion():
            width = min(frame.shape[1], dimensions[0] // 2)
            lines = [''.join(self.apply_pixel_to_ascii_strategy(pixel)
                             for pixel in row[:width]) for row in frame]
            if new_line_chars:
                return '\n'.join(lines) + '\n'
            padding = ' ' * max(dimensions[0] - width * 2, 0)
            return ''.join(line + padding for line in lines) + '\r\n'
        glyphs, ansi = self.frame_to_cells(frame, dimensions)
        if ansi is not None:
            chars = np.unique(glyphs)
            palette = getattr(self, '_palette', None)
            if palette is None:
                palette = self._palette = {}
            for c in chars:
                if (c, 0) not in palette:
                    palette.update({(c, a): f'\033[38;5;{a}m{c * 2}\033[0m'
                                    for a in range(256)})
            lines = [''.join(palette[c, int(a)] for c, a in zip(row, colors))
                     for row, colors in zip(glyphs, ansi)]
        else:
            lines = [''.join(c * 2 for c in row) for row in glyphs]
        if new_line_chars:
            return '\n'.join(lines) + '\n'
        padding = ' ' * max(dimensions[0] - glyphs.shape[1] * 2, 0)
        return ''.join(line + padding for line in lines) + '\r\n'

    def apply_end_line_modifier(self, msg):
        return msg

    def render(self, cap, output=None, output_format=None, with_audio=False,
               dimensions=DEFAULT_TERMINAL_SIZE, max_frames=None):
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        delay = 1 / fps
        file = None
        audio = None
        wave_file = None
        stream = None
        counter = 0
        started = time.perf_counter()
        try:
            if with_audio:
                import pyaudio
                wave_file = wave.open(str(Path(tempfile.gettempdir()) / 'temp-audiofile-for-vta.wav'), 'rb')
                audio = pyaudio.PyAudio()
                stream = audio.open(format=audio.get_format_from_width(wave_file.getsampwidth()),
                                    channels=wave_file.getnchannels(), rate=wave_file.getframerate(), output=True)
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                file = open(output, 'w', encoding='utf-8')
                if output_format == 'sh':
                    file.write("#!/usr/bin/env bash\nprintf '\\033[2J'\n")
                else:
                    file.write('[\n')
            else:
                sys.stdout.write('\033[2J')
            while cap.isOpened() and (max_frames is None or counter < max_frames):
                tick = time.perf_counter()
                ok, frame = cap.read()
                if not ok:
                    break
                msg = self.convert_frame_pixels_to_ascii(self.resize_frame(frame, dimensions), dimensions, True)
                if stream:
                    stream.write(wave_file.readframes(int(wave_file.getframerate() / fps)))
                if file:
                    if output_format == 'sh':
                        # %b interprets ANSI escapes without treating text as a format string.
                        escaped = ('\033[H' + msg).replace('\\', '\\\\').replace('\033', '\\033').replace("'", "'\\''")
                        file.write("printf '%b' '" + escaped + "'\n")
                        file.write(f'sleep {delay:.9f}\n')
                    else:
                        if counter:
                            file.write(',\n')
                        json.dump(msg.splitlines(), file, ensure_ascii=True)
                else:
                    sys.stdout.write('\033[H' + msg)
                    sys.stdout.flush()
                    time.sleep(max(0, delay - (time.perf_counter() - tick)))
                counter += 1
                if file and counter % 100 == 0:
                    print(f'Frames: {counter}/{int(total) or "?"}', file=sys.stderr)
            if not counter:
                raise RuntimeError('Video contains no decodable frames')
            if file and output_format == 'json':
                file.write('\n]\n')
        finally:
            if file:
                file.close()
            if stream:
                stream.close()
            if audio:
                audio.terminate()
            if wave_file:
                wave_file.close()
        elapsed = time.perf_counter() - started
        print(f'Rendered {counter} frames in {elapsed:.2f}s ({counter / elapsed:.1f} fps)', file=sys.stderr)

    def build_progress(self, progress, total):
        return f'{progress}/{int(total) or "?"}'

    def resize_frame(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
        height, width = frame.shape[:2]
        cols, rows = dimensions
        scale = min((cols // 2) / width, (rows - 1) / height)
        target = (max(1, int(width * scale)), max(1, int(height * scale)))
        if target == (width, height):
            return frame
        return cv2.resize(frame, target, interpolation=cv2.INTER_LINEAR)

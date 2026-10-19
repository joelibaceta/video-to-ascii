"""
This module contains a class AsciiColorStrategy, to process video frames and build an ascii output
"""

import time
import sys
import os
import cv2
import tempfile
import json
import shutil
import wave
from pathlib import Path
import numpy as np

PLATFORM = 0
if sys.platform != 'win32':
    PLATFORM = 1

from . import render_strategy as re
if PLATFORM:
    from . import image_processor as ipe
else:
    from . import image_processor_win as ipe
from os import get_terminal_size as _term_size
DEFAULT_TERMINAL_SIZE = tuple(shutil.get_terminal_size((120, 40)))

class AsciiStrategy(re.RenderStrategy):
    """Print each frame in the terminal using ascii characters"""

    def convert_frame_pixels_to_ascii(self, frame, dimensions=DEFAULT_TERMINAL_SIZE, new_line_chars=False):
        """
        Replace all pixels with colored chars and return the resulting string

        This method iterates each pixel of one video frame
        respecting the dimensions of the printing area
        to truncate the width if necessary
        and use the pixel_to_ascii method to convert one pixel
        into a character with the appropriate color.
        Finally joins the set of chars in a string ready to print.

        Args:
            frame: a single video frame
            dimensions: an array with the printing area dimensions
                in pixels [rows, cols]
            new_line_chars: if should append a new line character
                at end of each row

        Returns:
            str: The resulting set of colored chars as a unique string

        """
        if getattr(self, 'renderer', None) is not None:
            return self._convert_accelerated(frame, dimensions, new_line_chars)
        cols, _ = dimensions
        h, w, _ = frame.shape

        printing_width = int(min(int(cols), (w*2))/2)
        pad = max(int(cols) - printing_width*2, 0)


        msg = ''
        for j in range(h-1):
            for i in range(printing_width):
                pixel = frame[j][i]
                msg += self.apply_pixel_to_ascii_strategy(pixel)
            if new_line_chars:
                msg += "\n"
            else:
                msg += " " * (pad)
        msg += "\r\n"
        return msg

    def apply_pixel_to_ascii_strategy(self, pixel):
        return ipe.pixel_to_ascii(pixel)

    def apply_end_line_modifier(self, msg):
        return msg

    def render(self, cap, output=None, output_format=None, with_audio=False,
               dimensions=DEFAULT_TERMINAL_SIZE, max_frames=None):
        """
        Iterate each video frame to print a set of ascii chars

        This method reads each video frame from a opencv video capture
        resizing the frame and truncate the width if necessary to
        print correctly the final string built with the method
        convert_frame_pixels_to_ascii.
        Finally each final string is printed correctly, if the process
        was done too fast will sleep the necessary time to comply
        with the fps expected (30 fps by default).

        Args:
            cap: An OpenCV video capture
            output: If the render should be exported to a bash file
        """

        if getattr(self, 'renderer', None) is not None:
            return self._render_accelerated(cap, output, output_format, with_audio,
                                            dimensions, max_frames)

        v_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        v_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps or 30

        if with_audio:
            import pyaudio
            import wave

            temp_dir = tempfile.gettempdir()
            temp_file_path = temp_dir + "/temp-audiofile-for-vta.wav"
            wave_file = wave.open(temp_file_path, 'rb')
            chunk = int(wave_file.getframerate() / fps)
            p = pyaudio.PyAudio()

            stream = p.open(format =
                p.get_format_from_width(wave_file.getsampwidth()),
                channels = wave_file.getnchannels(),
                rate = wave_file.getframerate(),
                output = True)

            data = wave_file.readframes(chunk)


        if output is not None:
            file = open(output, 'w+')

            if output_format == 'sh':
                file.write("#!/bin/bash \n")
                file.write("echo -en '\033[2J' \n")
                file.write("echo -en '\u001b[0;0H' \n")

        time_delta = 1./fps
        counter=0
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            sys.stdout.write('\033[2J')
        # read each frame
        while cap.isOpened():
            t0 = time.process_time()
            if PLATFORM:
                rows, cols = os.popen('stty size', 'r').read().split()
            else:
                cols, rows = os.get_terminal_size()
            _ret, frame = cap.read()
            if frame is None:
                break
            if with_audio:
                data = wave_file.readframes(chunk)
                stream.write(data)
            # sleep if the process was too fast
            if output is None:
                if PLATFORM:
                    sys.stdout.write('\u001b[0;0H')
                else:
                    sys.stdout.write("\x1b[0;0H")
                # scale each frame according to terminal dimensions
                resized_frame = self.resize_frame(frame, (cols, rows))
                # convert frame pixels to colored string
                msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows))
                t1 = time.process_time()
                delta = time_delta - (t1 - t0)
                if delta > 0:
                    time.sleep(delta)
                sys.stdout.write(msg) # Print the final string
            else:
                print(self.build_progress(counter, length))
                if PLATFORM:
                    print("\u001b[2A")
                else:
                    print("\x1b[2A")

                if output_format == 'sh':
                    resized_frame = self.resize_frame(frame)
                    msg = self.convert_frame_pixels_to_ascii(resized_frame, new_line_chars=True)
                    file.write("sleep 0.033 \n")
                    file.write("echo -en '" + msg + "'" + "\n" )
                    file.write("echo -en '\u001b[0;0H' \n")
                elif output_format == 'json':
                    # scale each frame according to terminal dimensions
                    resized_frame = self.resize_frame(frame, (cols, rows))
                    msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows), new_line_chars=True)
                    lines = msg.split("\n")
                    # remove last line breaks (\n\r) which generate two extra unwanted array elements
                    lines = lines[0:-2]
                    # opening brackets
                    file.write("[[\n" if counter == 0  else ",[\n")
                    for i in range(len(lines)):
                        file.write(f"\"{lines[i]}\"")
                        # closing brackets
                        file.write("]\n" if i == (len(lines) - 1)  else ",\n")

            counter += 1
        if with_audio:
            stream.close()
            p.terminate()
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            os.system('cls') or None

        # close the frame array
        if output is not None and output_format == 'json':
            file.write(f"]\n")

    def build_progress(self, progress, total):
        """Build a progress bar in the terminal"""
        progress_percent =  int(progress / total * 100)
        adjusted_size_percent = int((20 / 100) * progress_percent)
        progress_bar = ('█' * adjusted_size_percent) + ('░' * (20-adjusted_size_percent))
        return  "  " +  "|" +  progress_bar + "| " + str(progress_percent) + "%"

    def resize_frame(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
        """
        Resize a frame to meet the terminal dimensions

        Calculating the output terminal dimensions (cols, rows),
        we can get a reduction factor to resize the frame
        according to the height of the terminal mainly
        to print each frame at a time, using all the available rows

        Args:
            frame: Frame to resize
            dimensions: If you want to set a printer area size (cols, rows)
        Returns:
            A resized frame
        """
        if getattr(self, 'renderer', None) is not None:
            return self._resize_accelerated(frame, dimensions)
        height, width, _ = frame.shape
        _, rows = dimensions
        reduction_factor = (float(rows)) / height * 100
        reduced_width = int(width * reduction_factor / 100)
        reduced_height = int(height * reduction_factor / 100)
        dimension = (reduced_width, reduced_height)
        resized_frame = cv2.resize(frame, dimension, interpolation=cv2.INTER_LINEAR)
        return resized_frame


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


    def frame_to_cells(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
        renderer = getattr(self, 'renderer', None)
        if renderer is None:
            from ..backends.cpu import CpuRenderer
            renderer = CpuRenderer(self)
        return renderer.frame_to_cells(frame[:, :dimensions[0] // 2])


    def _convert_accelerated(self, frame, dimensions=DEFAULT_TERMINAL_SIZE,
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


    def _render_accelerated(self, cap, output=None, output_format=None, with_audio=False,
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


    def _resize_accelerated(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
        height, width = frame.shape[:2]
        cols, rows = dimensions
        scale = min((cols // 2) / width, (rows - 1) / height)
        target = (max(1, int(width * scale)), max(1, int(height * scale)))
        if target == (width, height):
            return frame
        return cv2.resize(frame, target, interpolation=cv2.INTER_LINEAR)

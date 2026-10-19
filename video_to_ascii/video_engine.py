"""This module has a class for video processing"""

import cv2
import shutil
import copy
import inspect
from pathlib import Path
from .capture import open_capture
from .backends import normalize_backend, create_renderer
from . import render_strategy as re

class VideoEngine:
    """
    A class to encapsulate a video processing methods and persist variables across the process
    """

    def __init__(self, strategy="default", backend="cpu", columns=None, rows=None, max_frames=None, quality="standard", output_size=None):
        strategy_object = copy.copy(re.STRATEGIES[strategy])
        self.render_strategy = strategy_object
        self.read_buffer = None
        self.with_audio = False
        size = shutil.get_terminal_size((120, 40))
        self._extended_rendering = columns is not None or rows is not None or max_frames is not None
        self.dimensions = (columns or size.columns, rows or size.lines)
        self.backend = normalize_backend(backend)
        self.max_frames = max_frames
        self.quality = quality
        self.output_size = output_size

    def set_strategy(self, strategy):
        """
        Set a render strategy
        """
        strategy_object = copy.copy(re.STRATEGIES[strategy])
        self.render_strategy = strategy_object

    def load_video_from_file(self, filename):
        """
        Load a video file into the engine and set a read buffer
        """
        cap = (cv2.VideoCapture(filename) if self.backend == 'cpu'
               else open_capture(filename, self.backend, self.dimensions))
        self.read_buffer = cap
        self.filename = filename

    def play(self, output=None, output_format=None):
        """
        Play the video captured using an specific render strategy
        """
        
        extended = self.backend != 'cpu' or self._extended_rendering
        if output and output_format is None and (extended or Path(output).suffix.lower() == '.mp4'):
            output_format = Path(output).suffix.lower().lstrip('.')
        if output and extended and output_format not in ('sh', 'json', 'mp4'):
            self.read_buffer.release()
            raise ValueError('Output must have a .sh or .json or .mp4 extension')
        try:
            conversion = getattr(self.render_strategy, '_uses_builtin_pixel_conversion', None)
            custom_pixels = conversion is not None and not conversion()
            if custom_pixels and (self.backend in ('cuda', 'metal') or output_format == 'mp4'):
                raise RuntimeError('GPU and MP4 rendering require a built-in pixel converter')
            if output_format == 'mp4':
                from .mp4_export import export_mp4
                export_mp4(self.read_buffer, self.render_strategy, self.filename,
                           output, self.dimensions, self.max_frames, self.backend, self.quality, self.output_size)
                return
            if not custom_pixels and extended:
                self.render_strategy.renderer = create_renderer(self.backend, self.render_strategy)
            options = dict(output=output, output_format=output_format,
                           with_audio=self.with_audio)
            parameters = inspect.signature(self.render_strategy.render).parameters
            if 'dimensions' in parameters:
                options['dimensions'] = self.dimensions
            if 'max_frames' in parameters:
                options['max_frames'] = self.max_frames
            self.render_strategy.render(self.read_buffer, **options)
        finally:
            self.read_buffer.release()

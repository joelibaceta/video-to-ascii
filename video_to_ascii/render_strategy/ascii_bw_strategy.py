"""
This module contains a class AsciiColorStrategy, o process video frames and build an ascii output
"""

import time
import sys
import os
import cv2

from . import ascii_strategy as strategy
from .. import image_processor as ipe

class AsciiBWStrategy(strategy.AsciiStrategy):
    """Print each frame in the terminal using ascii characters"""

    def convert_frame_pixels_to_ascii(self, frame):
        """
        Replace all pixeles with chars and return the resulting string

        This method iterates each pixel of one video frame
        respecting the dimensions of the printing area
        to truncate the width if necessary
        and use the pixel_to_ascii method to convert one pixel
        into an appropriate character.
        Finally joins the set of chars in a string ready to print.

        Args:
            frame: a single video frame
            dimensions: an array with the printing area dimensions
                in pixels [rows, cols]

        Returns:
            str: The resulting set of chars as a unique string

        """
        _, cols = os.popen('stty size', 'r').read().split()
        h, w, _ = frame.shape
        printing_width = int(min(int(cols), (w*2))/2)
        padding_right = max(int(cols) - (w*2), 0)
        msg = ''
        for j in range(h):
            for i in range(printing_width):
                pixel = frame[j][i]
                ascii_char = ipe.pixel_to_ascii(pixel, colored=False)
                msg += ascii_char
            msg += (" " * padding_right)
        msg += "\r\n"
        return msg

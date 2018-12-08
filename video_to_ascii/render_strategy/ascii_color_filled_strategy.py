"""
This module contains a class AsciiColorStrategy, o process video frames and build an ascii output
"""

from . import ascii_strategy as strategy
from . import image_processor as ipe

class AsciiColorFilledStrategy(strategy.AsciiStrategy):
    """Print each frame in the terminal using ascii characters"""

    def apply_pixel_to_ascii_strategy(self, pixel):
        """
        Define a pixel parsing strategy to use high density colored chars

        Args:
            pixel: a single video frame

        Returns:
            str: The resulting set of colored chars as a unique string
        """
        return ipe.pixel_to_ascii(pixel, colored=False)

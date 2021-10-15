"""
This module contains a class AsciiColorStrategy, to process video frames and build an ascii output
"""

from . import ascii_strategy as strategy
import sys
if sys.platform != 'win32':
    from . import image_processor as ipe
else:
    from . import image_processor_win as ipe

class AsciiBWStrategy(strategy.AsciiStrategy):
    """Print each frame in the terminal using one color ascii characters"""

    def apply_pixel_to_ascii_strategy(self, pixel):
        """
        Define a pixel parsing strategy to use colored chars

        Args:
            pixel: a single video frame

        Returns:
            str: The resulting set of chars as a unique string
        """
        return ipe.pixel_to_ascii(pixel, colored=0)

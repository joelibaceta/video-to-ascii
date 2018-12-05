"""
This module contains a class AsciiColorStrategy, o process video frames and build an ascii output
"""

import time
import sys
import os
import cv2

from . import ascii_strategy as strategy
from .. import image_processor as ipe

class AsciiColorStrategy(strategy.AsciiStrategy):
    """Print each frame in the terminal using ascii characters"""

    def convert_frame_pixels_to_ascii(self, frame):
        """
        Replace all pixeles with colored chars and return the resulting string

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

        Returns:
            str: The resulting set of colored chars as a unique string

        """
        _, cols = os.popen('stty size', 'r').read().split()
        h, w, _ = frame.shape
        printing_width = int(min(int(cols), (w*2))/2)
        padding_right = max(int(cols) - (w*2), 0)
        msg = ''
        for j in range(h):
            for i in range(printing_width):
                pixel = frame[j][i]
                colored_ascii_char = ipe.pixel_to_ascii(pixel, density=1)
                msg += colored_ascii_char
            msg += (" " * padding_right)
        msg += "\r\n"
        return msg

    def render(self, vc):
        """
        Iterate each video frame to print a set of ascii chars

        This method read each video frame from a opencv video capture
        resizing the frame and truncate the width if necessary to
        print correcly the final string builded with the method
        convert_frame_pixels_to_ascii.
        Finally each final string is printed correctly, if the process
        was done too fast will sleep the necessary time to comply
        with the fps expected (30 fps by default).

        Args:
            vc: An OpenCV video capture
        """

        v_width = vc.get(cv2.CAP_PROP_FRAME_WIDTH)
        v_height = vc.get(cv2.CAP_PROP_FRAME_HEIGHT)

        fps = 30
        time_delta = 1./fps
        # read each frame
        while(vc.isOpened()):
            t0 = time.clock()
            _ret, frame = vc.read()
            if (frame is None):
                break
            # scale each frame according to terminal dimensions
            resized_frame = self.resize_frame(frame)
            # convert frame pixels to colored string
            str = self.convert_frame_pixels_to_ascii(resized_frame)
            # sleep if the process was too fast
            sys.stdout.write('\u001b[0;0H')
            t1 = time.clock()
            delta = time_delta - (t1 - t0)
            if (delta > 0):
                time.sleep(delta)
            # Print the final string
            sys.stdout.write(str)
            

    def resize_frame(self, frame):
        """
        Resize a frame to meet the terminal dimensions

        Calculating the output terminal dimensions (cols, rows),
        we can to get a reduction factor to resize the frame 
        according to the height of the terminal mainly 
        to print each frame at a time, using all the available rows

        Args:
            frame: Frame to resize
        Returns:
            A resized frame
        """
        h, w, _ = frame.shape
        rows, _ = os.popen('stty size', 'r').read().split()
        reduction_factor = (float(rows)-1) / h * 100
        reduced_width = int(w * reduction_factor / 100)
        reduced_height = int(h * reduction_factor / 100)
        dimension = (reduced_width, reduced_height)
        resized_frame = cv2.resize(frame, dimension, interpolation=cv2.INTER_LINEAR)
        return resized_frame
        
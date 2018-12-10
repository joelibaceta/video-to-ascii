"""
This module contains a class AsciiColorStrategy, o process video frames and build an ascii output
"""

import time
import sys
import os
import cv2
import tempfile 

from . import render_strategy as re
from . import image_processor as ipe

DEFAULT_TERMINAL_SIZE = 80, 25

class AsciiStrategy(re.RenderStrategy):
    """Print each frame in the terminal using ascii characters"""

    def convert_frame_pixels_to_ascii(self, frame, dimensions=DEFAULT_TERMINAL_SIZE, new_line_chars=False):
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
            new_line_chars: if should append a new line character
                at end of each row

        Returns:
            str: The resulting set of colored chars as a unique string

        """
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

    def render(self, cap, output=None, with_audio=False):
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
            cap: An OpenCV video capture
            output: If the render should be exported to a bash file
        """

        v_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        v_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)

        if with_audio:
            import pyaudio
            import wave

            temp_dir = tempfile.gettempdir()
            temp_file_path = temp_dir + "/temp-audiofile-for-vta.wav"
            wave_file = wave.open(temp_file_path, 'rb')
            chunk = int(44100 / fps)
            p = pyaudio.PyAudio()

            stream = p.open(format =
                p.get_format_from_width(wave_file.getsampwidth()),
                channels = wave_file.getnchannels(),
                rate = wave_file.getframerate(),
                output = True)
                       
            data = wave_file.readframes(chunk)
            

        if output is not None:
            file = open(output, 'w+')
            file.write("#!/bin/bash \n")
            file.write("echo -en '\033[2J' \n")
            file.write("echo -en '\u001b[0;0H' \n")

        time_delta = 1./fps
        counter=0
        sys.stdout.write("echo -en '\033[2J' \n")
        # read each frame
        while cap.isOpened():


            t0 = time.clock()
            rows, cols = os.popen('stty size', 'r').read().split()
            _ret, frame = cap.read()
            if frame is None:
                break
            if with_audio:
                data = wave_file.readframes(chunk)
                stream.write(data)
            # sleep if the process was too fast
            if output is None:
                sys.stdout.write('\u001b[0;0H')
                # scale each frame according to terminal dimensions
                resized_frame = self.resize_frame(frame, (cols, rows))
                # convert frame pixels to colored string
                msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows)) 
                t1 = time.clock()
                delta = time_delta - (t1 - t0)
                if delta > 0:
                    time.sleep(delta)
                sys.stdout.write(msg) # Print the final string
            else:
                print(self.build_progress(counter, length))
                print("\u001b[2A")
                resized_frame = self.resize_frame(frame)
                msg = self.convert_frame_pixels_to_ascii(resized_frame, new_line_chars=True)
                file.write("sleep 0.033 \n")
                file.write("echo -en '" + msg + "'" + "\n" ) 
                file.write("echo -en '\u001b[0;0H' \n")
            counter += 1
        if with_audio:
            stream.close()
            p.terminate() 
        sys.stdout.write("echo -en '\033[2J' \n")

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
        we can to get a reduction factor to resize the frame
        according to the height of the terminal mainly
        to print each frame at a time, using all the available rows

        Args:
            frame: Frame to resize
            dimensions: If you want to set a printer area size (cols, rows)
        Returns:
            A resized frame
        """
        height, width, _ = frame.shape
        _, rows = dimensions
        reduction_factor = (float(rows)) / height * 100
        reduced_width = int(width * reduction_factor / 100)
        reduced_height = int(height * reduction_factor / 100)
        dimension = (reduced_width, reduced_height)
        resized_frame = cv2.resize(frame, dimension, interpolation=cv2.INTER_LINEAR)
        return resized_frame
        
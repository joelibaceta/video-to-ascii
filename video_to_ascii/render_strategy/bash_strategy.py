from . import render_strategy as strategy
from . import image_processor as ipe
import cv2

class BashStrategy(strategy.RenderStrategy):

    DEFAULT_TERMINAL_SIZE = 80, 25

    def build_frame_string(self, frame):
        cols, rows  = self.DEFAULT_TERMINAL_SIZE
        h, w, _ = frame.shape
        printing_width = int(min(int(cols), (w*2))/2)
        padding_right = max(int(cols) - (w*2), 0)
        str = ''
        for j in range(h):
            for i in range(printing_width):
                pixel = frame[j][i]
                str += ipe.pixel_to_ascii(pixel, density=1) 
            str += "\n"
        return str

    def render(self, vc, output=None):
        v_width = vc.get(cv2.CAP_PROP_FRAME_WIDTH)
        v_height = vc.get(cv2.CAP_PROP_FRAME_HEIGHT)
        file = open(output, 'w+')
        file.write("#!/bin/bash \n")
        file.write("echo -en '\u001b[0;0H' \n")
        while(vc.isOpened()):
            _ret, frame = vc.read()
            if (frame is None):
                break
            resized_frame = self.resize_frame(frame)
            str = self.build_frame_string(resized_frame)
            file.write("sleep 0.033 \n")
            file.write("echo -en '" + str + "'" + "\n" ) 
            file.write("echo -en '\u001b[0;0H' \n")

    def resize_frame(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
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
        _, rows = dimensions
        reduction_factor = (rows-1) / h * 100
        reduced_width = int(w * reduction_factor / 100)
        reduced_height = int(h * reduction_factor / 100)
        dimension = (reduced_width, reduced_height)
        resized_frame = cv2.resize(frame, dimension, interpolation=cv2.INTER_LINEAR)
        return resized_frame
        
import os
import cv2
import sys
from .image_processor import processor
from .video_processor import engine
import time

def play(filename):

    fps = 30
    time_delta = 1./fps
    str = ''

    rows, columns = os.popen('stty size', 'r').read().split()
    reader, frames_count = engine.load_video_frames(filename) 

    while(reader.isOpened()):
        
        t0 = time.clock()

        width = reader.get(cv2.CAP_PROP_FRAME_WIDTH)   # float
        height = reader.get(cv2.CAP_PROP_FRAME_HEIGHT) # float

        REDUCTION_PERCENT = (float(rows)-1) / height * 100

        reduced_width = int(width * REDUCTION_PERCENT / 100)
        reduced_height = int(height * REDUCTION_PERCENT / 100)

        fill_left_with_blank = int(columns) - (reduced_width * 2) 
    
        # read frame by frame
        ret, frame = reader.read()
        frame = engine.rescale_frame(frame, percent=REDUCTION_PERCENT)
        
        for j in range(reduced_height): 
            for i in range(reduced_width):
                pixel = frame[j][i]
                ascii_char = processor.pixel_to_ascii(pixel) 
                str += ascii_char
            str += (" " * fill_left_with_blank)
        str += "\r\n"

        t1 = time.clock()
        delta = time_delta - (t1 - t0)
        if (delta > 0):
            time.sleep(delta)
        sys.stdout.write( str )
        str = ''


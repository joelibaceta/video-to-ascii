import os
import cv2
import numpy as np
import sys
from image_processor import processor
from video_processor import engine
import time

fps = 30
time_delta = 1./fps

rows, columns = os.popen('stty size', 'r').read().split()

clear = lambda: os.system('clear')

filename = sys.argv[1:][0]
reader, frames_count = engine.load_video_frames(filename) 


counter = 0

while(reader.isOpened()):

    t0 = time.clock()

    width = reader.get(cv2.CAP_PROP_FRAME_WIDTH)   # float
    height = reader.get(cv2.CAP_PROP_FRAME_HEIGHT) # float

    REDUCTION_PERCENT = (float(rows)-1) / height * 100

    reduced_width = int(width * REDUCTION_PERCENT / 100)
    reduced_height = int(height * REDUCTION_PERCENT / 100)

    # read frame by frame
    ret, frame = reader.read()
    frame = engine.rescale_frame(frame, percent=REDUCTION_PERCENT)
    str = ''
    for j in range(reduced_height): 
        for i in range(reduced_width):
            pixel = frame[j][i]
            ascii_char = processor.pixel_to_ascii(pixel) 
            str += ascii_char
        str += "\n"

    t1 = time.clock()
    delta = time_delta - (t1 - t0)
    if (delta > 0):
        time.sleep(delta)

    print str
    counter += 1
    
file.close()
reader.release()
cv2.destroyAllWindows()


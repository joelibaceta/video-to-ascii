import cv2

def load_video_frames(filename):
    cap = cv2.VideoCapture(filename) 
    cap.set(cv2.CAP_PROP_FPS, 10)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    return cap, length

def rescale_frame(frame, percent=75):
    width = int(frame.shape[1] * percent/ 100)
    height = int(frame.shape[0] * percent/ 100)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation =cv2.INTER_AREA)


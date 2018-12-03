"""This module has a class for video processing"""

import cv2
from . import render_strategy as re

class VideoEngine:
    """
    A class to encapsulate a video processing methods and persist variables across the process
    """

    def __init__(self, strategy="default"):
        strategy_object = re.STRATEGIES[strategy]
        self.render_strategy = strategy_object
        self.read_buffer = None

    def set_strategy(self, strategy):
        """
        Set a render strategy
        """
        strategy_object = re.STRATEGIES[strategy]
        self.render_strategy = strategy_object

    def load_video_from_file(self, filename):
        """
        Load a video file into the engine and set a read buffer
        """
        cap = cv2.VideoCapture(filename)
        self.read_buffer = cap

    def play(self):
        """
        Play the video captured using an specific render strategy
        """
        self.render_strategy.render(self.read_buffer)

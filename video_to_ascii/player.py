"""This module contains a set of functions to use the video_to_ascii from cli"""

from . import video_engine as ve

def play(filename, **kwargs):
    """
    Play a video from a file by default using ascii chars in terminal
    """
    engine = ve.VideoEngine()
    if "strategy" in kwargs:
        engine.set_strategy(kwargs["strategy"])
    engine.load_video_from_file(filename)
    engine.play()

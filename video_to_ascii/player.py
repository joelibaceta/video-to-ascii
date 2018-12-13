"""This module contains a set of functions to use the video_to_ascii from cli"""

from video_to_ascii.core import audio_engine
from video_to_ascii.core.video_engine import VideoEngine


def play(filename, strategy=None, output=None, play_audio=False):
    """
    Play or export a video from a file by default using ascii chars in terminal
    """
    v_engine = VideoEngine()

    v_engine.load_video_from_file(filename)
    if  play_audio:
        audio_engine.extract_audio_track_from_video_file(filename)
        v_engine.with_audio = True
    if strategy is not None:
        v_engine.set_strategy(strategy)

    v_engine.play(output)

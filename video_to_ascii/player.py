"""This module contains a set of functions to use the video_to_ascii from cli"""

import tempfile
from . import video_engine as ve

def play(filename, strategy=None, output=None, output_format=None, play_audio=False, backend="cpu", columns=None, rows=None, max_frames=None, quality="standard"):
    """
    Play or export a video from a file by default using ascii chars in terminal
    """
    output_size = None
    mp4 = output and (output_format == 'mp4' or str(output).lower().endswith('.mp4'))
    if mp4 and columns is None and rows is None:
        from .mp4_export import source_dimensions
        (columns, rows), output_size = source_dimensions(filename)
    engine = ve.VideoEngine(backend=backend, columns=columns, rows=rows,
                            max_frames=max_frames, quality=quality, output_size=output_size)
    engine.load_video_from_file(filename)
    if play_audio and not (output and (output_format == 'mp4' or output.lower().endswith('.mp4'))):
        import ffmpeg
        temp_dir = tempfile.gettempdir()
        temp_file_path = temp_dir + "/temp-audiofile-for-vta.wav"
        stream = ffmpeg.input(filename)
        stream = ffmpeg.output(stream, temp_file_path)
        stream = ffmpeg.overwrite_output(stream)
        ffmpeg.run(stream)
        engine.with_audio = True
    if strategy is not None:
        engine.set_strategy(strategy)
    engine.play(output, output_format)

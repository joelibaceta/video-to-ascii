import tempfile
import ffmpeg
import pyaudio
import wave


def extract_audio_track_from_video_file(video_path):
    temp_dir = tempfile.gettempdir()
    temp_file_path = temp_dir + "/temp-audiofile-for-vta.wav"

    stream = ffmpeg.input(video_path)
    stream = ffmpeg.output(stream, temp_file_path)
    stream = ffmpeg.overwrite_output(stream)
    ffmpeg.run(stream)

class AudioEngine:

    def open_audio_port(self):
        self.pyaudio = pyaudio.PyAudio()

        self.audio_port_stream = self.pyaudio.open(format=
                             self.pyaudio.get_format_from_width(
                                 self.wave_file.getsampwidth()),
                             channels=self.wave_file.getnchannels(),
                             rate=self.wave_file.getframerate(),
                             output=True)

    def load_audio_stream(self, fps):
        temp_dir = tempfile.gettempdir()
        temp_file_path = temp_dir + "/temp-audiofile-for-vta.wav"
        self.wave_file = wave.open(temp_file_path, 'rb')
        self.chunk_size = int(44100 / fps)
        self.open_audio_port()

    def play_audio_chunk(self):
        data = self.wave_file.readframes(self.chunk_size)
        self.audio_port_stream.write(data)

    def close(self):
        self.audio_port_stream.close()
        self.pyaudio.terminate()

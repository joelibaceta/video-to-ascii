"""Rasterize the ASCII cells and encode a playable H.264 MP4."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .backends import backend_for, normalize_backend, create_renderer
from .colors import PALETTE
from .render_strategy.image_processor import DENSITY


class CellRasterizer:
    """Cache glyph masks; color and tile an entire frame with NumPy."""
    def __init__(self, dimensions, output_size=None):
        font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
        if not font_path.exists():
            try:
                font_path = subprocess.check_output(
                    ['fc-match', '-f', '%{file}', 'monospace'], text=True).strip()
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError('MP4 export requires a monospace TrueType font') from exc
        font = ImageFont.truetype(str(font_path), 16)
        self.cell_width = int(np.ceil(font.getlength('M'))) * 2
        self.cell_height = 20
        self.width = dimensions[0] // 2 * self.cell_width
        self.height = (dimensions[1] - 1) * self.cell_height
        if output_size is not None:
            self.width, self.height = output_size
        chars = list(dict.fromkeys(c for density in DENSITY for c in density))
        self.char_index = {char: i for i, char in enumerate(chars)}
        masks = []
        for char in chars:
            mask = Image.new('L', (self.cell_width, self.cell_height))
            ImageDraw.Draw(mask).text((0, 0), char * 2, font=font, fill=255)
            masks.append(np.asarray(mask))
        self.masks = np.array(masks)
        self.palette = PALETTE

    def render(self, glyphs, ansi):
        indices = np.array([[self.char_index[c] for c in row] for row in glyphs])
        masks = self.masks[indices].astype(np.uint16)
        colors = self.palette[ansi] if ansi is not None else np.full((*glyphs.shape, 3), 255, dtype=np.uint8)
        pixels = (masks[..., None] * colors[:, :, None, None, :] // 255).astype(np.uint8)
        rows, cols = glyphs.shape
        tiled = pixels.transpose(0, 2, 1, 3, 4).reshape(rows * self.cell_height, cols * self.cell_width, 3)
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        top = (self.height - tiled.shape[0]) // 2
        left = (self.width - tiled.shape[1]) // 2
        canvas[top:top + tiled.shape[0], left:left + tiled.shape[1]] = tiled
        return canvas


def source_dimensions(filename):
    """Derive a glyph grid and MP4 canvas from the displayed source resolution."""
    metadata = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_streams', '-of', 'json', filename], text=True))['streams'][0]
    width, height = metadata['width'], metadata['height']
    rotation = int(next((s.get('rotation', 0) for s in metadata.get('side_data_list', [])
                         if 'rotation' in s), metadata.get('tags', {}).get('rotate', 0))) % 360
    if rotation in (90, 270):
        width, height = height, width
    metrics = CellRasterizer((4, 3))
    if width < metrics.cell_width or height < metrics.cell_height:
        raise ValueError('Source is too small for ASCII glyphs; specify --columns and --rows')
    dimensions = (width // metrics.cell_width * 2, height // metrics.cell_height + 1)
    # YUV 4:2:0 requires even dimensions; add at most one pixel per axis.
    return dimensions, (width + width % 2, height + height % 2)


def encoder_options(encoder, quality):
    if encoder == 'h264_nvenc':
        return (['-preset', 'p7', '-tune', 'lossless', '-rc', 'constqp', '-qp', '0']
                if quality == 'lossless' else ['-preset', 'p4', '-cq', '18', '-b:v', '0'])
    if encoder == 'h264_videotoolbox':
        return ['-allow_sw', '0', '-q:v', '75']
    return ['-preset', 'slow', '-crf', '0'] if quality == 'lossless' else ['-preset', 'fast', '-crf', '18']


def select_encoder(backend, quality='standard', dimensions=(256, 256)):
    """Probe codec/quality support; auto also validates the output dimensions."""
    backend = normalize_backend(backend)
    target = backend_for(backend)
    if target == 'cpu' or (target == 'metal' and quality == 'lossless'):
        return 'libx264'
    encoder = 'h264_videotoolbox' if target == 'metal' else 'h264_nvenc'
    # Explicit GPU modes never fall back for unsupported output dimensions, so
    # avoid a redundant full-size encode before the real conversion. Auto needs
    # the full configuration to decide whether to use the CPU encoder instead.
    width, height = dimensions if backend == 'auto' else (256, 256)
    command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', f'color=s={width}x{height}',
               '-frames:v', '1', '-c:v', encoder, *encoder_options(encoder, quality), '-f', 'null', '-']
    try:
        probe = subprocess.run(command, capture_output=True)
        if probe.returncode == 0:
            return encoder
        reason = probe.stderr.decode(errors='replace')
    except OSError as exc:
        reason = str(exc)
    if backend != 'auto':
        raise RuntimeError(f'{encoder} encoder failed: {reason}')
    print(f'{encoder} unavailable; using CPU encoding: {reason}', file=sys.stderr)
    return 'libx264'


def export_mp4(cap, strategy, filename, output, dimensions, max_frames, backend, quality="standard", output_size=None):
    if Path(filename).resolve() == Path(output).resolve():
        raise ValueError('MP4 output must differ from input')
    if quality not in ('standard', 'lossless'):
        raise ValueError('Unknown MP4 quality')
    rasterizer = CellRasterizer(dimensions, output_size)
    renderer = create_renderer(backend, strategy, rasterizer)
    strategy.renderer = renderer
    pixel_format = renderer.pixel_format
    encoder = select_encoder(backend, quality, (rasterizer.width, rasterizer.height))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    print(f'MP4 encoder: {encoder}; {rasterizer.width}x{rasterizer.height}', file=sys.stderr)
    audio_args = ['-c:a', 'aac', '-b:a', '192k']
    if quality == 'lossless':
        audio_codec = subprocess.check_output(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', filename], text=True).strip()
        audio_args = ['-c:a', 'copy'] if audio_codec in ('aac', 'mp3', 'alac', '') else ['-c:a', 'alac']
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    # Encode into a temporary file, then replace the requested output only on success.
    with tempfile.TemporaryDirectory(dir=Path(output).parent) as temporary:
        target = Path(temporary) / 'ascii.mp4'
        command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                   '-threads', '2', '-filter_threads', '1', '-filter_complex_threads', '1',
                   '-f', 'rawvideo', '-pix_fmt', pixel_format,
                   '-s', f'{rasterizer.width}x{rasterizer.height}',
                   '-r', str(fps), '-i', 'pipe:0', '-i', filename,
                   '-map', '0:v:0', '-map', '1:a:0?', '-c:v', encoder]
        command += encoder_options(encoder, quality)
        # Full exports must flush every frame; -shortest and duration cutoffs
        # can discard buffered frames at fractional source frame rates.
        if max_frames:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            limit = min(frame_count, max_frames) if frame_count else max_frames
            command += ['-t', f'{limit / fps:.9f}']
        command += ['-pix_fmt', 'yuv420p', *audio_args,
                    '-movflags', '+faststart', str(target)]
        counter = 0
        started = time.perf_counter()
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)
            try:
                while cap.isOpened() and (max_frames is None or counter < max_frames):
                    ok, frame = cap.read()
                    if not ok:
                        break
                    frame = strategy.resize_frame(frame, dimensions)
                    pixels = renderer.render_frame(frame)
                    process.stdin.write(pixels)
                    counter += 1
                    if counter % 100 == 0:
                        print(f'MP4 frames: {counter}', file=sys.stderr)
                process.stdin.close()
                code = process.wait()
                if code or not counter:
                    errors.seek(0)
                    raise RuntimeError(errors.read().decode(errors='replace') or 'No MP4 frames generated')
            except BrokenPipeError as exc:
                process.wait()
                errors.seek(0)
                raise RuntimeError(errors.read().decode(errors='replace') or 'MP4 encoder stopped') from exc
            finally:
                if process.poll() is None:
                    process.terminate()
                if not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except BrokenPipeError:
                        pass
                process.wait()
        target.replace(output)
    elapsed = time.perf_counter() - started
    print(f'Exported {counter} ASCII frames to {output} in {elapsed:.2f}s', file=sys.stderr)

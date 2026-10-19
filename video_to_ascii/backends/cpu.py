"""NumPy implementation of the shared frame-renderer contract."""
import numpy as np

from ..colors import nearest_ansi, normalize_rgb
from ..render_strategy.image_processor import DENSITY


class CpuRenderer:
    name = 'cpu'
    pixel_format = 'rgb24'

    def __init__(self, strategy):
        from ..render_strategy.ascii_bw_strategy import AsciiBWStrategy
        from ..render_strategy.ascii_color_filled_strategy import AsciiColorFilledStrategy
        self.colored = not isinstance(strategy, AsciiBWStrategy)
        density = 2 if isinstance(strategy, AsciiColorFilledStrategy) else (1 if self.colored else 0)
        self.chars = np.array(DENSITY[density])
        self.weights = np.array([0.267, 0.642, 0.091] if self.colored else [0.2126, 0.7152, 0.0722])

    def frame_to_cells(self, frame):
        if (frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3
                or not frame.shape[0] or not frame.shape[1]):
            raise ValueError('CPU frames must be nonempty uint8 BGR arrays')
        brightness = frame[..., ::-1].astype(np.float64) @ self.weights
        indices = np.clip((brightness * (len(self.chars)-1) / 255 + 1e-12).astype(int), 0, len(self.chars)-1)
        ansi = nearest_ansi(normalize_rgb(frame)) if self.colored else None
        return self.chars[indices], ansi

    def configure_raster(self, rasterizer):
        if (rasterizer.width <= 0 or rasterizer.height <= 0
                or rasterizer.width % 2 or rasterizer.height % 2):
            raise ValueError('Raster dimensions must be positive and even')
        self.rasterizer = rasterizer

    def render_frame(self, frame):
        return self.rasterizer.render(*self.frame_to_cells(frame)).tobytes()

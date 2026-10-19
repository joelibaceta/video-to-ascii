"""Xterm palette and nearest color mapping shared by CPU and CUDA rendering."""
import numpy as np

LEVELS = np.array([0, 95, 135, 175, 215, 255], dtype=np.int32)
PALETTE = np.array([[0, 0, 0]] * 16 +
                   [[r, g, b] for r in LEVELS for g in LEVELS for b in LEVELS] +
                   [[8 + i * 10] * 3 for i in range(24)], dtype=np.uint8)


def nearest_ansi(rgb):
    """Find the exact nearest of the 240 fixed xterm colors in RGB distance."""
    rgb = np.asarray(rgb, dtype=np.int32)
    cube = np.abs(rgb[..., None] - LEVELS).argmin(axis=-1)
    cube_index = 16 + cube[..., 0] * 36 + cube[..., 1] * 6 + cube[..., 2]
    cube_error = ((rgb - LEVELS[cube]) ** 2).sum(axis=-1)
    # The nearest gray minimizes the sum of channel distances around their mean.
    gray = np.clip(np.ceil((rgb.mean(axis=-1) - 8) / 10 - 0.5), 0, 23).astype(int)
    gray_error = ((rgb - (8 + gray[..., None] * 10)) ** 2).sum(axis=-1)
    return np.where(gray_error < cube_error, 232 + gray, cube_index).astype(np.uint8)


def normalize_rgb(frame):
    """Preserve float64 saturation/truncation on CPU, including for Metal input."""
    rgb = frame[..., ::-1].astype(np.float64)
    high = rgb.max(axis=2, keepdims=True)
    low = rgb.min(axis=2, keepdims=True)
    saturation = np.divide(high-low, high, out=np.zeros_like(high), where=high != 0)
    ratio = np.divide(np.minimum(saturation+0.3, 1), saturation,
                      out=np.ones_like(high), where=saturation != 0)
    return np.clip(high-(high-rgb)*ratio, 0, 255).astype(np.uint8)

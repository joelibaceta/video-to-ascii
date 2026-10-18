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

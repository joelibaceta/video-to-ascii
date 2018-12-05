from . import ascii_bw_strategy as bw
from . import ascii_color_strategy as color
from . import ascii_color_filled_strategy as filled

STRATEGIES = {
    "default": color.AsciiColorStrategy(),
    "ascii-color": color.AsciiColorStrategy(),
    "just-ascii": bw.AsciiBWStrategy(),
    "filled-ascii": filled.AsciiColorFilledStrategy()
}
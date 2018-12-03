from xtermcolor import colorize
import colorsys

CHARS_LIGHT = ['@', '#', '$', '=', '*', '!', ';', ':', '~', '-', ',', '.', ' ', ' ']
CHARS_FILLED = ['█', '▓', '▒', '░', '□']

def brightness_to_ascii(i, density=0):
    """
    Get an apropiate char of brighnes from a rgb color
    """
    chars_collection = CHARS_LIGHT
    if density == 1:
        chars_collection = CHARS_FILLED
    max, min = len(chars_collection), 0
    index = int((i-min) / (max - min))
    return chars_collection[index]

def colorize_char(char, ansi_color):
    """
    Get an apropiate char of brighnes from a rgb color
    """
    str_colorized = colorize(char, ansi=ansi_color)
    return str_colorized

def pixel_to_ascii(pixel, colored=True):
    """
    Convert a pixel to char
    """
    char = ''
    if colored:
        b, g, r = pixel[0], pixel[1], pixel[2]
        h, s, v = colorsys.rgb_to_hsv(float(r), float(g), float(b))
        s = s + 0.3 if s + 0.3 < 1.0 else 1.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        bright = rgb_to_brightness(pixel)
        char = brightness_to_ascii(bright)
        ansi_color = rgb_to_ansi(r, g, b)
        char = colorize(char*2, ansi=ansi_color)
    else:
        bright = rgb_to_brightness(pixel)
        char = brightness_to_ascii(bright, 0)
    return char

def rgb_to_brightness(rgb):
    """
    Calc a brighness factor according to rgb color
    """
    return int((rgb[0] + rgb[1] + rgb[2]) / 3)

def rgb_to_ansi(r, g, b):
    """
    Convert an rgb color to ansi color
    """
    r, g, b = int(r), int(g), int(b)
    if (r == g & g == b):
        if (r < 8):
            return int(16)
        if (r > 248):
            return int(230)
        return int(round(((r - 8) / 247) * 24) + 232)
    r_in_ansi_range = int(round(float(r) / 51))
    g_in_ansi_range = int(round(float(g) / 51))
    b_in_ansi_range = int(round(float(b) / 51))
    ansi = 16 + (36 * r_in_ansi_range) + (6 * g_in_ansi_range) + b_in_ansi_range
    return int(ansi)

    

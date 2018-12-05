from xtermcolor import colorize
import colorsys

CHARS_LIGHT = [' ', ' ', '.', ':', '!', '+', '*', 'e', '$', '@', '8']
CHARS_COLOR = ['.', '*', 'e', 's', '◍']
CHARS_FILLED = ['░', '▒', '▓', '█']

DENSITY = [CHARS_LIGHT, CHARS_COLOR, CHARS_FILLED]

def brightness_to_ascii(i, density=0):
    """
    Get an apropiate char of brighnes from a rgb color
    """
    chars_collection = DENSITY[density]
    size = len(chars_collection) - 1
    index = int(size * i / 255) #int((i / 255) * size) 
    return chars_collection[index]

def colorize_char(char, ansi_color):
    """
    Get an apropiate char of brighnes from a rgb color
    """
    str_colorized = colorize(char, ansi=ansi_color)
    return str_colorized

def pixel_to_ascii(pixel, colored=True, density=0):
    """
    Convert a pixel to char
    """
    b, g, r = pixel[0], pixel[1], pixel[2]
    char = ''
    if colored:
        h, s, v = colorsys.rgb_to_hsv(float(r), float(g), float(b))
        bright = rgb_to_brightness(r, g, b)
        s = s + 0.3 if s + 0.3 < 1.0 else 1.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        char = brightness_to_ascii(bright, density)
        ansi_color = rgb_to_ansi(r, g, b)
        char = colorize(char*2, ansi=ansi_color)
    else:
        bright = rgb_to_brightness(r, g, b, grayscale=True)
        char = brightness_to_ascii(bright, density)
        char = char*2
    return char

def rgb_to_brightness(r, g, b, grayscale=False):
    """
    Calc a brighness factor according to rgb color
    """
    if grayscale:
        return 0.2126*r + 0.7152*g + 0.0722*b
    else:
        return 0.267*r + 0.642*g + 0.091*b

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

    

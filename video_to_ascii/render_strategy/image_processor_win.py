"""Module with useful functions to image processing"""
"""Windows-compatibility module"""

from colored import fg, attr
import colorsys

CHARS_LIGHT = [' ', ' ', '.', ':', '!', '+', '*', 'e', '$', '@', '8']
CHARS_COLOR = ['.', '*', 'e', 's', '◍']
CHARS_FILLED = ['░', '▒', '▓', '█']

DENSITY = [CHARS_LIGHT, CHARS_COLOR, CHARS_FILLED]

def rgb_to_colorhex(r, g, b):
    R = format(int(r), 'x')
    if len(R) == 1:
        R = '0'+format(int(r), 'x')
    G = format(int(g), 'x')
    if len(G) == 1:
        G = '0'+format(int(g), 'x')
    B = format(int(b), 'x')
    if len(B) == 1:
        B = '0'+format(int(b), 'x')
    return f'#{R.upper()}{G.upper()}{B.upper()}'

def brightness_to_ascii(i, density=0):
    """
    Get an appropriate char of brightness from a rgb color
    """
    chars_collection = DENSITY[density]
    size = len(chars_collection) - 1
    index = int(size * i / 255)
    return chars_collection[index]

def colorize_char(char, colorhex):
    """
    Get an appropriate char of brightness from a rgb color
    """
    str_colorized = fg(colorhex)+char+attr('reset')
    return str_colorized

def pixel_to_ascii(pixel, colored=True, density=0):
    """
    Convert a pixel to char
    """
    bgr = tuple(float(x) for x in pixel[:3])
    rgb = tuple(reversed(bgr))
    char = ''
    if colored:
        bright = rgb_to_brightness(*rgb)
        rgb = increase_saturation(*rgb)
        char = brightness_to_ascii(bright, density)
        hex_color = rgb_to_colorhex(*rgb)
        char = fg(hex_color)+char*2+attr('reset')
    else:
        bright = rgb_to_brightness(*rgb, grayscale=True)
        char = brightness_to_ascii(bright, density)
        char = char*2
    return char

def increase_saturation(r, g, b):
    """
    Increase the saturation from rgb and return the new value as rgb tuple
    """
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = min(s+0.3, 1.0)
    return colorsys.hsv_to_rgb(h, s, v)

def rgb_to_brightness(r, g, b, grayscale=False):
    """
    Calc a brightness factor according to rgb color
    """
    if grayscale:
        return 0.2126*r + 0.7152*g + 0.0722*b
    else:
        return 0.267*r + 0.642*g + 0.091*b

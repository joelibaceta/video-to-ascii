from xtermcolor import colorize
from . import color
import colorsys

CHARS = ['@','#','$','=','*','!',';',':','~','-',',','.',' ', ' ']

def optimize(x):
    max, min = 13, 0
    return  (x-min) / (max - min)

def colorize_char(char, ansi_color):
    str_colorized = colorize(char, ansi=ansi_color)
    return str_colorized

def pixel_to_ascii(pixel):
    b, g, r = pixel[0], pixel[1], pixel[2]
  
    h, s, v = colorsys.rgb_to_hsv(float(r), float(g), float(b))
    s = s + 0.3 if s + 0.3 < 1.0 else 1.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)

    bright = color.rgb_to_brightness(pixel)
    char = brightness_to_ascii(bright)
    ansi_color = color.rgb_to_ansi(r, g, b)

    str_color = colorize(char + "o", ansi=ansi_color)
    return str_color

def brightness_to_ascii(bright):
    i = int(optimize(bright))
    return CHARS[i]


    

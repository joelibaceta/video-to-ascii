from xtermcolor import colorize

CHARS = ['@','#','$','=','*','!',';',':','~','-',',','.',' ', ' ']

def optimize(x):
    max, min = 13, 0
    return  (x-min) / (max - min)

def colorize_char(char, ansi_color):
    str_colorized = colorize(char, ansi=ansi_color)
    return str_colorized

def pixel_to_ascii(pixel):
    b, g, r = pixel[0], pixel[1], pixel[2]
    bright = rgb_to_brightness(pixel)
    char = brightness_to_ascii(bright)
    
    ansi_color = rgb_to_ansi(r, g, b)
    str_color = colorize(char + ":", ansi=ansi_color)

    return str_color

def rgb_to_brightness(rgb):
    return int((rgb[0] + rgb[1] + rgb[2]) / 3)

def brightness_to_ascii(bright):
    i = optimize(bright)
    return CHARS[i]

def rgb_to_ansi(r, g, b): 
    
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
    
def rgb2hex(color):
    string = '0x'
    for value in color:
        hex_string = hex(value)  
        reduced_hex_string = hex_string[2:] 
        capitalized_hex_string = reduced_hex_string.upper() 
        string += capitalized_hex_string  
    return string
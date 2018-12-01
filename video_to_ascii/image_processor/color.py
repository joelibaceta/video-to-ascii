import math

def rgb_to_brightness(rgb):
    return int((rgb[0] + rgb[1] + rgb[2]) / 3)

def rgb_to_ansi(r, g, b): 

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

def rgb_to_hex(color):
    string = '0x'
    for value in color:
        hex_string = hex(value)  
        reduced_hex_string = hex_string[2:] 
        capitalized_hex_string = reduced_hex_string.upper() 
        string += capitalized_hex_string  
    return string

 
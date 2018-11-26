from image_processor import processor
from image_processor import color
import colorsys

r, g, b = 45.0, 226.0, 219.0

ansi_color = color.rgb_to_ansi(r, g, b)

print(processor.colorize_char(ansi_color, ansi_color))

h, s, v = colorsys.rgb_to_hsv(r, g, b)
print h, s, v
r, g, b = colorsys.hsv_to_rgb(h, s, v)
print r, g, b
 
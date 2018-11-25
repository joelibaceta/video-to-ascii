from image_processor import processor

ansi_color = processor.rgb_to_ansi(135, 87, 57)




print ansi_color
print(processor.colorize_char(ansi_color, ansi_color))

number = ansi_color

rgb_R = ((number - 16) // 36) * 51
rgb_G = (((number - 16) % 36) // 6) * 51
rgb_B = ((number - 16) % 6) * 51

print rgb_R, rgb_G, rgb_B
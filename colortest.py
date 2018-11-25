#!/usr/bin/python
"""Print a swatch using all 256 colors of 256-color-capable terminals."""


__author__ = "Marius Gedminas <marius@gedmin.as>"
__url__ = "https://gist.github.com/mgedmin/2762225"
__version__ = '2.0'


def hrun(start, width, padding=0):
    return [None] * padding + list(range(start, start + width)) + [None] * padding

def vrun(start, width, height, padding=0):
    return [hrun(s, width, padding)
            for s in range(start, start + width * height, width)]

layout = [
    vrun(0, 8, 2),                # 16 standard xterm colors
    vrun(16, 6, 6 * 6, 1),        # 6x6x6 color cube
    vrun(16 + 6 * 6 * 6, 8, 3),   # 24 grey levels
]


def fg_seq(color):
    return '\033[38;5;%dm' % color


def bg_seq(color):
    return '\033[48;5;%dm' % color

reset_seq = '\033[0m'


def color_bar(seq, color, trail):
    if color is None:
        return '%s    %s' % (reset_seq, trail)
    else:
        return '%s %03d%s' % (seq(color), color, trail)


def main():
    for block in layout:
        print("")
        for row in block:
            fg_bar = ''.join(color_bar(fg_seq, color, '') for color in row)
            bg_bar = ''.join(color_bar(bg_seq, color, ' ') for color in row)
            print('%s%s    %s%s' % (fg_bar, reset_seq, bg_bar, reset_seq))


if __name__ == '__main__':
    main()
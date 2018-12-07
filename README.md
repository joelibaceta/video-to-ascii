![Logo](images/logo.png)
<br/><br/>
It's a simple python package to play videos in a terminal using [ASCII](https://en.wikipedia.org/wiki/ASCII) characters.

[![PyPI version](https://badge.fury.io/py/video-to-ascii.svg)](https://badge.fury.io/py/video-to-ascii)
[![Maintainability](https://api.codeclimate.com/v1/badges/a5fcdf2b0cab41654ca3/maintainability)](https://codeclimate.com/github/joelibaceta/video-to-terminal/maintainability)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/joelibaceta/video-to-ascii)
[![HitCount](http://hits.dwyl.io/joelibaceta/https://github.com/joelibaceta/video-to-ascii.svg)](http://hits.dwyl.io/joelibaceta/https://github.com/joelibaceta/video-to-ascii)

![frames](images/Simpsons.apng)

## Installation
```bash
pip install video-to-ascii
```

> The installation should copy the main script to your PATH and making it available for general use.

## How to use

Just run `video-to-ascii` in your terminal

```bash
$ video-to-ascii -f myvideo.mp4
```

### Options

**--strategy**
Allow to choose an strategy to render the output

![strategies](images/Strategies.png)

**-o --output**
Export the rendering output to a bash file to share with someone

![strategies](images/export.png)

<br/>

## How it works

Every video is composed by a set of frames that are played at a certain frame rate.

![frames](images/imgVideoFrames.png)

Since a terminal has a specific number of rows and columns, we have to resize our video to adjust to the terminal size limitations.

![frames](images/imgTerminal.png)

To reach a correct visualization of an entire frame we need to adjust the _frame height_ to match the _terminal rows_, avoiding using more _characters_ than the number of _terminal columns_.

![frames](images/imgResizing.png)

When picking a character to represent a pixel we need to measure the relevance of that pixel's color in the frame, based on that we can then select the most appropriate character based on the [relative luminance](https://en.wikipedia.org/wiki/Relative_luminance) in colorimetric spaces, using a simplify version of the luminosity function.

![LuminosityFunction](images/Luminosity.svg)

> Green light contributes the most to the intensity perceived by humans, and blue light the least.


This function returns an integer in the range from 0 to 255, we assign a character according to density to show more colored surface for areas with more intense color (highest values).

```python
CHARS_LIGHT 	= [' ', ' ', '.', ':', '!', '+', '*', 'e', '$', '@', '8']
CHARS_COLOR 	= ['.', '*', 'e', 's', '@']
CHARS_FILLED    = ['░', '▒', '▓', '█']
```

<br/>

The reduced range of colors supported by the terminal is a problem we need to account for. Modern terminals support up to 256 colors, so we need to find the closest 8 bit color that matches the original pixel in 16 or 24 bit color, we call this set of 256 colors [ANSI colors](https://stackoverflow.com/questions/4842424/list-of-ansi-color-escape-sequences).

![frames](images/imgPixelSection.png)

![colors](images/8-bit_color_table.png)

Finally, when putting it all together, we will have an appropriate character for each pixel and a new color.

![frames](images/imgPixelImage.png)


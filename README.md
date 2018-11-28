![Logo](images/logo.svg)

Its a simple python package to play videos through terminal characters.

# Installation

```python
pip install video-to-ascii
```
> The installation will copy the main script to your PATH and making it available for general use.

# How to use

Just run in your terminal `video-to-ascii` + your video path.

```bash
video-to-ascii myvideo.mp4
```

## How it works

Every videos is composed by a set of frames that was played at a certain frame rate.

![frames](images/imgVideoFrames.png)

Because a terminal has an specific number of rows and columns, we have to resize our video to adjust to the terminal size limitations.

![frames](images/imgTerminal.png)

To reach a correct visualization of entire frame we need to adjust the frame height to terminal rows, avoiding using more than characters than the number of terminal columns.

![frames](images/imgFrameResize.png)

To choose a character to represent one pixel we need to evaluate the relevance of a pixel color in the frame choosing the most appropriate character according to its intensity for each pixel.

![frames](images/imgBrightnes.png)

The reduced range of colors supported by the terminal is another problem, in modern terminals we have up to 256 colors supported, so we will have to find the closest 8 bits color to the original  pixel color, we call this set of 256 colors as ANSI colors.

![frames](images/imgPixelSection.png)

Finally, if we put all togheter, we will have an appropriate character for each pixel and a new color.

![frames](images/imgPixelImage.png)


#!/usr/bin/env python

import argparse
from video_to_ascii import player

CLI_DESC = "It is a simple python package to play videos in the terminal using colored characters as pixels or other useful outputs"
EPILOG = ("\033[1;37mThanks for trying video-to-ascii!\033[0m")

PARSER = argparse.ArgumentParser(prog='video-to-ascii', description=CLI_DESC, epilog=EPILOG)
PARSER.add_argument('-f', '--file', type=str, dest='file', help='input video file', action='store', required=True)
PARSER.add_argument('--strategy', default='ascii-color', type=str, dest='strategy', 
    choices=["ascii-color", "just-ascii", "filled-ascii"], help='choose an strategy to render the output', action='store')
PARSER.add_argument('-o', '--output', type=str, dest='output', help='output file to export', action='store')
PARSER.add_argument('--output-format', default='sh', type=str, dest='output_format', 
    choices=["sh", "json"], help='choose an output format to render the output', action='store')
PARSER.add_argument('--with-audio', dest='with_audio', help='play audio', action='store_true')

ARGS = PARSER.parse_args()

player.play(ARGS.file, strategy=ARGS.strategy, output=ARGS.output, output_format=ARGS.output_format, play_audio=ARGS.with_audio)

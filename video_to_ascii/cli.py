"""This module contains a CLI interface"""

from . import player

def main():
    import argparse

    CLI_DESC = "It is a simple python package to play videos in the terminal using colored characters as pixels or other useful outputs"
    EPILOG = ("\033[1;37mThanks for trying video-to-ascii!\033[0m")

    PARSER = argparse.ArgumentParser(prog='video-to-ascii', description=CLI_DESC, epilog=EPILOG)
    PARSER.add_argument('-f', '--file', type=str, dest='file', help='input video file', action='store', required=True)
    PARSER.add_argument('--strategy', default='ascii-color', type=str, dest='strategy', 
        choices=["ascii-color", "just-ascii", "filled-ascii"], help='choose an strategy to render the output', action='store')
    PARSER.add_argument('-o', '--output', type=str, dest='output', help='export to .mp4, .sh, or .json', action='store')
    PARSER.add_argument('-a','--with-audio', dest='with_audio', help='play audio track', action='store_true')

    PARSER.add_argument('--backend', choices=['auto', 'cuda', 'metal', 'mlx', 'cpu'], default='cpu',
                        help='processing backend; mlx aliases metal; explicit GPU modes require acceleration')
    PARSER.add_argument('--columns', type=int, default=None, help='output terminal columns')
    PARSER.add_argument('--rows', type=int, default=None, help='output terminal rows')
    PARSER.add_argument('--max-frames', type=int, default=None, help='limit frames for a quick test')
    PARSER.add_argument('--quality', choices=['standard', 'lossless'], default='standard',
                        help='MP4 encoding quality; lossless creates larger files')
    ARGS = PARSER.parse_args()
    if ARGS.columns is not None and ARGS.columns < 4:
        PARSER.error('--columns must be at least 4')
    if ARGS.rows is not None and ARGS.rows < 3:
        PARSER.error('--rows must be at least 3')
    if ARGS.max_frames is not None and ARGS.max_frames < 1:
        PARSER.error('--max-frames must be positive')

    try:
        player.play(ARGS.file, strategy=ARGS.strategy, output=ARGS.output, play_audio=ARGS.with_audio, backend=ARGS.backend,
                    columns=ARGS.columns, rows=ARGS.rows, max_frames=ARGS.max_frames, quality=ARGS.quality)
    except (RuntimeError, OSError, ValueError) as exc:
        PARSER.exit(1, f'video-to-ascii: {exc}\n')
    except (KeyboardInterrupt):
        pass

if __name__ == '__main__':
    main()

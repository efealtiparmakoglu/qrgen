"""Command line interface for qrgen."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .matrix import make


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrgen",
        description="Generate QR codes in the terminal (ANSI half blocks), "
        "as ASCII, or as SVG. Implements the QR spec from scratch: "
        "Reed-Solomon over GF(256), BCH format/version codes, and mask "
        "penalty scoring. Byte mode (UTF-8).",
    )
    parser.add_argument("text", nargs="?", help="text to encode ('-' or omitted: read stdin)")
    parser.add_argument("-l", "--level", choices=("L", "M", "Q", "H"), default="M",
                        help="error correction level (default: M)")
    parser.add_argument("--version", type=int, default=None, metavar="1-40",
                        help="force a symbol version instead of auto-sizing")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="write an SVG to FILE instead of the terminal")
    parser.add_argument("--ascii", action="store_true",
                        help="ASCII rendering ('#'/space) instead of ANSI blocks")
    parser.add_argument("--invert", action="store_true",
                        help="flip module polarity in terminal rendering "
                        "(for light-background terminals)")
    parser.add_argument("-q", "--quiet-zone", type=int, default=4, metavar="N",
                        help="quiet zone width in modules (default 4; "
                        "spec recommends 4)")
    parser.add_argument("-V", "--version-info", action="version",
                        version=f"qrgen {__version__}")
    return parser


def main(argv: "list[str] | None" = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.text is None or args.text == "-":
        if sys.stdin.isatty():
            parser.error("no text given (pass it as an argument or pipe it)")
        text = sys.stdin.buffer.read()
    else:
        text = args.text.encode("utf-8")

    try:
        matrix = make(text, level=args.level, version=args.version)
    except ValueError as exc:
        print(f"qrgen: {exc}", file=sys.stderr)
        return 1

    if args.quiet_zone < 0 or (args.version is not None and args.version > 40):
        print("qrgen: invalid --quiet-zone or --version", file=sys.stderr)
        return 2

    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(matrix.render_svg(quiet=args.quiet_zone))
                fh.write("\n")
            info = f"{matrix.size}x{matrix.size}, version {matrix.version}, level {matrix.level}, mask {matrix.mask}"
            print(f"qrgen: wrote {args.output} ({info})")
        elif args.ascii:
            print(matrix.render_ascii(quiet=args.quiet_zone))
        else:
            print(matrix.render_terminal(invert=args.invert, quiet=args.quiet_zone))
    except OSError as exc:
        print(f"qrgen: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

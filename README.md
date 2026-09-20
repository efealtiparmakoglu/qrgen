# qrgen

**A from-scratch QR Code generator in pure Python — Reed-Solomon, BCH codes, mask scoring, zero dependencies.**

[![CI](https://github.com/efealtiparmakoglu/qrgen/actions/workflows/ci.yml/badge.svg)](https://github.com/efealtiparmakoglu/qrgen/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)

`qrgen` implements the QR Code specification (ISO/IEC 18004) end to end on
its own: GF(256) arithmetic, Reed-Solomon error correction, BCH-protected
format/version strings, the eight mask patterns with penalty scoring, and
all 40 symbol versions — then renders to the terminal (ANSI half blocks),
plain ASCII, or standalone SVG.

```
$ qrgen "MERHABA DUNYA" --ascii -q 2
  #######   # # #######
  #     # ### # #     #
  # ### #    ## # ### ##
  ...
```

## Why qrgen

- **The spec, from scratch.** No `qrcode` library under the hood — every
  table, polynomial and placement rule in this repo was implemented and
  tested directly against ISO/IEC 18004. Byte mode (UTF-8), versions 1–40,
  levels L/M/Q/H.
- **Zero dependencies.** Pure Python 3.9+ standard library. The only
  third-party code involved is in the *optional* scanner conformance harness
  (`pyzbar`), which is a dev tool, not a dependency.
- **Scanner-verified.** The development harness renders symbols to PNG and
  confirms an external barcode scanner (zbar) reads back the original text
  across all levels and versions, up to the 2953-byte v40-L capacity.
- **Three renderers.** ANSI half-blocks for crisp terminals (with
  `--invert` for light themes), ASCII for logs, and SVG for print/web.

## Install

```sh
pip install .          # from a clone
qrgen "hello"          # console script
```

Or without installing: `python3 -m qrgen.cli "hello"`.

## Usage

```sh
qrgen "text"                    # terminal, ANSI half blocks
qrgen "text" --ascii            # '#' and ' ' rendering
qrgen "text" -o qr.svg          # standalone SVG (black on white)
qrgen -l H "important"          # highest error correction
qrgen --version 5 -l Q "data"   # force a symbol version
echo "piped" | qrgen -          # read stdin
```

| Option | Meaning |
|---|---|
| `-l, --level L\|M\|Q\|H` | error correction level (default M) |
| `--version 1-40` | force a symbol version instead of auto-sizing |
| `-o, --output FILE` | write SVG instead of the terminal |
| `--ascii` | ASCII rendering |
| `--invert` | flip module polarity (light terminal themes) |
| `-q, --quiet-zone N` | quiet zone width in modules (default 4) |

## The implementation

| Module | Contents |
|---|---|
| `qrgen/gf.py` | GF(256) log/exp tables over polynomial 0x11D |
| `qrgen/rs.py` | Reed-Solomon generator polynomials and check symbols |
| `qrgen/spec.py` | capacity/EC-block/alignment tables, BCH format & version codes |
| `qrgen/encoder.py` | byte-mode bitstream, terminator/padding, block interleaving |
| `qrgen/matrix.py` | function patterns, zigzag placement, 8 masks + penalty scoring |
| `qrgen/render.py` / `cli.py` | ANSI / ASCII / SVG renderers and the CLI |

Mask penalty scoring follows the four spec rules (run-length N1, 2×2 blocks
N2, finder-like patterns N3, dark-ratio deviation N4); the lowest-penalty
mask wins. Function patterns are never masked, and the dark module is always
preserved.

## Development

```sh
python3 -m unittest discover -s tests   # core suite (stdlib only)
./scripts/conformance.py                # optional: scanner-level verification
```

The core suite covers GF identities, RS syndrome validity, BCH code
properties, capacity/block-layout consistency across all 160 level×version
combinations, bitstream structure, function-pattern invariants (masking must
never touch finders, timing, alignment, version info or the dark module),
renderers and a golden matrix regression.

The optional conformance harness (`scripts/conformance.py`, requires
`pyzbar` + `pillow` in a scratch venv) renders symbols as PNGs and verifies
that an external scanner reads back the original text — 72 dense payloads
across every level and versions 1/5/10/.../40.

## License

MIT — see [LICENSE](LICENSE).

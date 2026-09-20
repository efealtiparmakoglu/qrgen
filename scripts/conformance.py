#!/usr/bin/env python3
"""Scanner-level conformance harness (dev-only, NOT a project dependency).

Generates QR symbols across every level/version with dense payloads, renders
them to PNG, and verifies an external scanner decodes the original text.

Usage:
    python3 -m venv /tmp/qr-oracle
    /tmp/qr-oracle/bin/pip install pyzbar pillow
    /tmp/qr-oracle/bin/python scripts/conformance.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402
from pyzbar import pyzbar  # noqa: E402

from qrgen import make, spec  # noqa: E402


def to_png(matrix, path, scale=4, quiet=4):
    size = matrix.size
    total = size + 2 * quiet
    img = Image.new("L", (total, total), 255)
    px = img.load()
    for y, row in enumerate(matrix.modules):
        for x, dark in enumerate(row):
            if dark:
                px[quiet + x, quiet + y] = 0
    img = img.resize((total * scale, total * scale), Image.NEAREST)
    img.save(path)


def main() -> int:
    cases = []
    for level in spec.LEVELS:
        for v in (1, 5, 10, 15, 20, 25, 30, 35, 40):
            cap = spec.data_codewords(level, v) - 3
            cases.append(("A" * cap, level, v))  # dense repetitive payload
            varied = "".join(chr(33 + (i * 7) % 90) for i in range(cap))
            cases.append((varied, level, v))  # varied ASCII payload
    cases.append(("", "M"))
    cases.append(("türkçe-ışığğüçöİĞŞÇÜ", "M"))

    ok = fail = 0
    for text, level, version in cases:
        m = make(text, level=level, version=version)
        to_png(m, "/tmp/qrgen-conformance.png")
        res = pyzbar.decode(Image.open("/tmp/qrgen-conformance.png"))
        got = res[0].data.decode("utf-8") if res else None
        if got == text:
            ok += 1
        else:
            fail += 1
            print(f"FAIL {level} v{version} mask={m.mask} len={len(text)}")
    print(f"conformance: {ok} scanned, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

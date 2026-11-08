"""QR Code specification tables: raw codeword counts, error-correction block
layout, alignment pattern coordinates, and the BCH format/version codes.
Byte-mode only by design (this tool encodes text, and UTF-8 is bytes)."""
from __future__ import annotations

from typing import Final

# Error-correction levels and their 2-bit codes used in the format info
# (deliberately not in MSB order — this is the QR spec's mapping).
LEVELS: Final = ("L", "M", "Q", "H")
FORMAT_ECL_BITS: Final = {"L": 1, "M": 0, "Q": 3, "H": 2}
LEVEL_INDEX: Final = {name: i for i, name in enumerate(LEVELS)}

# Raw data codewords available in the symbol for each version 1..40 (before
# splitting into blocks and reserving EC codewords).
RAW_CODEWORDS: Final = (
    26, 44, 70, 100, 134, 172, 196, 242, 292, 346,
    404, 466, 532, 581, 655, 733, 815, 901, 991, 1085,
    1156, 1258, 1364, 1474, 1588, 1706, 1828, 1921, 2051, 2185,
    2323, 2465, 2611, 2761, 2876, 3034, 3196, 3362, 3532, 3706,
)

# ECC_CODEWORDS_PER_BLOCK[level][version-1]
ECC_PER_BLOCK: Final = {
    "L": (7, 10, 15, 20, 26, 18, 20, 24, 30, 18,
          20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
          28, 28, 30, 30, 26, 28, 30, 30, 30, 30,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "M": (10, 16, 26, 18, 24, 16, 18, 22, 22, 26,
          30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
          26, 28, 28, 28, 28, 28, 28, 28, 28, 28,
          28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    "Q": (13, 22, 18, 26, 18, 24, 18, 22, 20, 24,
          28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
          28, 30, 30, 30, 30, 28, 30, 30, 30, 30,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "H": (17, 28, 22, 16, 22, 28, 26, 26, 24, 28,
          24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
          30, 24, 30, 30, 30, 30, 30, 30, 30, 30,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
}

# NUM_ERROR_CORRECTION_BLOCKS[level][version-1]
NUM_BLOCKS: Final = {
    "L": (1, 1, 1, 1, 1, 2, 2, 2, 2, 4,
          4, 4, 4, 4, 6, 6, 6, 6, 7, 8,
          8, 9, 9, 10, 12, 12, 12, 13, 14, 15,
          16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    "M": (1, 1, 1, 2, 2, 4, 4, 4, 5, 5,
          5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
          17, 17, 18, 20, 21, 23, 25, 26, 28, 29,
          31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    "Q": (1, 1, 2, 2, 4, 4, 6, 6, 8, 8,
          8, 10, 12, 16, 12, 17, 16, 18, 21, 20,
          23, 23, 25, 27, 29, 34, 34, 35, 38, 40,
          43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    "H": (1, 1, 2, 4, 4, 4, 5, 6, 8, 8,
          11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
          25, 34, 30, 32, 35, 37, 40, 42, 45, 48,
          51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
}

# Alignment pattern center coordinates per version (index = version - 1).
ALIGNMENT: Final = (
    (), (6, 18), (6, 22), (6, 26), (6, 30), (6, 34),
    (6, 22, 38), (6, 24, 42), (6, 26, 46), (6, 28, 50),
    (6, 30, 54), (6, 32, 58), (6, 34, 62), (6, 26, 46, 66), (6, 26, 48, 70),
    (6, 26, 50, 74), (6, 30, 54, 78), (6, 30, 56, 82), (6, 30, 58, 86), (6, 34, 62, 90),
    (6, 28, 50, 72, 94), (6, 26, 50, 74, 98), (6, 30, 54, 78, 102), (6, 28, 54, 80, 106),
    (6, 32, 58, 84, 110),
    (6, 30, 58, 86, 114), (6, 34, 62, 90, 118), (6, 26, 50, 74, 98, 122),
    (6, 30, 54, 78, 102, 126), (6, 26, 52, 78, 104, 130),
    (6, 30, 56, 82, 108, 134), (6, 34, 60, 86, 112, 138), (6, 30, 58, 86, 114, 142),
    (6, 34, 62, 90, 118, 146), (6, 30, 54, 78, 102, 126, 150), (6, 24, 50, 76, 102, 128, 154),
    (6, 28, 54, 80, 106, 132, 158), (6, 32, 58, 84, 110, 136, 162), (6, 26, 54, 82, 110, 138, 166),
    (6, 30, 58, 86, 114, 142, 170),
)

MIN_VERSION: Final = 1
MAX_VERSION: Final = 40


def data_codewords(level: str, version: int) -> int:
    """Number of data codewords (after removing EC codewords)."""
    _check_level_version(level, version)
    blocks = NUM_BLOCKS[level][version - 1]
    return RAW_CODEWORDS[version - 1] - ECC_PER_BLOCK[level][version - 1] * blocks


def block_layout(level: str, version: int) -> tuple[int, int, int, int]:
    """Returns (short_block_data_len, num_short_blocks, long_block_data_len,
    num_long_blocks). Every block holds `ecc` check symbols."""
    _check_level_version(level, version)
    blocks = NUM_BLOCKS[level][version - 1]
    ecc = ECC_PER_BLOCK[level][version - 1]
    short_len = RAW_CODEWORDS[version - 1] // blocks - ecc
    num_long = RAW_CODEWORDS[version - 1] % blocks
    return short_len, blocks - num_long, short_len + 1, num_long


def format_bits(level: str, mask: int) -> int:
    """The 15-bit BCH-protected format string for a level/mask pair."""
    if mask < 0 or mask > 7:
        raise ValueError("mask must be 0..7")
    data = (FORMAT_ECL_BITS[level] << 3) | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return ((data << 10) | rem) ^ 0x5412


def version_bits(version: int) -> int:
    """The 18-bit BCH-protected version string (versions 7+)."""
    if version < 7 or version > MAX_VERSION:
        raise ValueError("version info only exists for versions 7..40")
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
    return (version << 12) | rem


def _check_level_version(level: str, version: int) -> None:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}")
    if version < MIN_VERSION or version > MAX_VERSION:
        raise ValueError(f"version must be {MIN_VERSION}..{MAX_VERSION}")

"""Byte-mode encoding: text -> version -> bitstream -> interleaved codewords.

Design note: only byte mode is implemented (mode indicator 0b0100). UTF-8
bytes cover every text input, numeric/alphanumeric modes would only shave
bit count for restricted alphabets.
"""
from __future__ import annotations

from . import spec
from .rs import remainder as rs_remainder

MODE_BYTE = 0b0100
PAD_BYTES = (0xEC, 0x11)


def char_count_bits(version: int) -> int:
    """Byte-mode character count field width for a version."""
    if version < 10:
        return 8
    return 16


def choose_version(text: bytes, level: str) -> int:
    """Smallest version whose capacity fits the byte-mode payload."""
    for version in range(spec.MIN_VERSION, spec.MAX_VERSION + 1):
        capacity_bits = spec.data_codewords(level, version) * 8
        if 4 + char_count_bits(version) + 8 * len(text) <= capacity_bits:
            return version
    v = spec.MAX_VERSION
    max_bytes = (spec.data_codewords(level, v) * 8 - 4 - char_count_bits(v)) // 8
    raise ValueError(
        f"data of {len(text)} bytes does not fit any version at level {level} "
        f"(max {max_bytes} bytes)"
    )


def build_bitstream(text: bytes, level: str, version: int) -> list[int]:
    """Full codeword sequence for a symbol: mode, count, data, terminator,
    pad bits/bytes, then data + EC blocks interleaved."""
    total_bits = spec.data_codewords(level, version) * 8
    cc_bits = char_count_bits(version)

    bits: list[int] = []
    append = lambda value, n: bits.extend((value >> (n - 1 - i)) & 1 for i in range(n))

    append(MODE_BYTE, 4)
    append(len(text), cc_bits)
    for byte in text:
        append(byte, 8)

    # Terminator: up to 4 zero bits, capped by capacity.
    append(0, min(4, total_bits - len(bits)))
    # Pad to a byte boundary.
    while len(bits) % 8 != 0:
        append(0, 1)
    # Pad codewords alternate 0xEC / 0x11.
    pad_byte = iter(PAD_BYTES * (total_bits // 8))
    while len(bits) < total_bits:
        append(next(pad_byte), 8)

    codewords = []
    for i in range(0, len(bits), 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        codewords.append(value)

    return interleave(codewords, level, version)


def interleave(data: list[int], level: str, version: int) -> list[int]:
    """Split data codewords into blocks, append each block's RS check
    symbols, then interleave data and check columns (QR block layout).

    Convention: the LONG blocks come first in the sequence (ISO/IEC 18004
    block numbering), i.e. blocks 0..num_long-1 carry long_len data."""
    short_len, num_short, long_len, num_long = spec.block_layout(level, version)
    ecc_len = spec.ECC_PER_BLOCK[level][version - 1]

    blocks: list[list[int]] = []
    pos = 0
    for i in range(num_short + num_long):
        length = short_len if i < num_short else long_len
        block = list(data[pos:pos + length])
        pos += length
        block.extend(rs_remainder(block, ecc_len))
        blocks.append(block)

    out: list[int] = []
    for i in range(long_len):
        for block in blocks:
            if i < len(block) - ecc_len:
                out.append(block[i])
    # EC columns: symbol i of every block's check section (each block's
    # check section starts at its own data length).
    for i in range(ecc_len):
        for block in blocks:
            out.append(block[len(block) - ecc_len + i])
    return out

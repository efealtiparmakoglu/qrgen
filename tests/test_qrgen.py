"""Unit + conformance tests for qrgen (stdlib unittest only).

An optional scanner-level conformance suite lives in scripts/conformance.py;
it needs pyzbar+pillow and is skipped here so the core suite stays
dependency-free.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qrgen import spec  # noqa: E402
from qrgen.encoder import build_bitstream, char_count_bits, choose_version  # noqa: E402
from qrgen.gf import div, inv, mul, pow  # noqa: E402
from qrgen.matrix import (  # noqa: E402
    _build_function_patterns,
    _mask_shift,
    _penalty,
    _place_data,
    make,
)
from qrgen.rs import generator, remainder  # noqa: E402


class TestGF(unittest.TestCase):
    def test_multiplication_identities(self):
        for a in (1, 7, 128, 255):
            self.assertEqual(mul(a, 1), a)
            self.assertEqual(mul(a, 0), 0)

    def test_inverse(self):
        for a in range(1, 256):
            self.assertEqual(mul(a, inv(a)), 1)

    def test_div(self):
        for a in (3, 44, 200):
            for b in (1, 5, 251):
                self.assertEqual(div(mul(a, b), b), a)

    def test_pow(self):
        self.assertEqual(pow(2, 8), 0x1D)  # x^8 reduces modulo 0x11D
        self.assertEqual(mul(pow(3, 5), pow(3, 250)), 1)


class TestRS(unittest.TestCase):
    def test_generator_degree(self):
        self.assertEqual(len(generator(10)), 11)
        self.assertEqual(generator(1), [1, 1])

    def test_codeword_polynomial_divisible_by_generator(self):
        # A valid RS codeword evaluates to zero at every generator root:
        # syndromes must all vanish.
        data = list(b"HELLO WORLD, THIS IS THE PAYLOAD")
        degree = 16
        gen = generator(degree)
        codeword = data + remainder(data, degree)
        for root_exp in range(degree):
            x = (1 << 8) | 0  # placeholder; evaluate via EXP table below
            # Evaluate via Horner using gf.mul
            from qrgen.gf import EXP
            value = 0
            alpha = EXP[root_exp % 255]
            for coef in codeword:
                value = mul(value, alpha) ^ coef
            self.assertEqual(value, 0, f"syndrome {root_exp} nonzero")


class TestSpec(unittest.TestCase):
    def test_format_codes_are_32_distinct(self):
        values = {spec.format_bits(level, mask) for level in spec.LEVELS for mask in range(8)}
        self.assertEqual(len(values), 32)
        # The 15-bit strings split into two BCH-decodable families; each must
        # decode to its (level, mask) via brute-force nearest-neighbor
        # (<= 3 bit errors correctable).
        table = {spec.format_bits(l, m): (l, m) for l in spec.LEVELS for m in range(8)}
        for v in values:
            near = [k for k in table if bin(k ^ v).count("1") <= 3]
            self.assertEqual(len(near), 1, f"{v:015b} not uniquely decodable")

    def test_version_codes(self):
        for v in range(7, 41):
            bits = spec.version_bits(v)
            self.assertEqual((bits >> 12) ^ v ^ 0x0, 0)  # sanity: v fits
        with self.assertRaises(ValueError):
            spec.version_bits(1)

    def test_capacities_monotonic_and_consistent(self):
        for level in spec.LEVELS:
            prev = 0
            for v in range(1, 41):
                data = spec.data_codewords(level, v)
                self.assertGreater(data, prev)
                sl, ns, ll, nl = spec.block_layout(level, v)
                blocks = ns + nl
                self.assertEqual(blocks, spec.NUM_BLOCKS[level][v - 1])
                self.assertEqual(sl * ns + ll * nl, data)
                self.assertEqual(
                    data + spec.ECC_PER_BLOCK[level][v - 1] * blocks,
                    spec.RAW_CODEWORDS[v - 1],
                )
                prev = data

    def test_char_count_widths(self):
        self.assertEqual(char_count_bits(1), 8)
        self.assertEqual(char_count_bits(9), 8)
        self.assertEqual(char_count_bits(10), 16)
        self.assertEqual(char_count_bits(40), 16)


class TestEncoder(unittest.TestCase):
    def test_choose_version_boundaries(self):
        # v1-M holds 14 data codewords: 4+8+8n bits -> n <= 14 bytes.
        self.assertEqual(choose_version(b"a" * 14, "M"), 1)
        self.assertEqual(choose_version(b"a" * 15, "M"), 2)

    def test_bitstream_structure(self):
        cw = build_bitstream(b"AB", "M", 1)
        self.assertEqual(len(cw), 26)
        bits = []
        for v in cw:
            bits += [(v >> (7 - i)) & 1 for i in range(8)]
        self.assertEqual(bits[:4], [0, 1, 0, 0])  # byte mode
        count = 0
        for b in bits[4:12]:
            count = (count << 1) | b
        self.assertEqual(count, 2)

    def test_all_levels_all_versions_produce_full_codewords(self):
        for level in spec.LEVELS:
            for v in range(1, 41):
                cw = build_bitstream(b"sample payload", level, v)
                self.assertEqual(len(cw), spec.RAW_CODEWORDS[v - 1])


class TestMatrix(unittest.TestCase):
    def test_function_pattern_invariants(self):
        for version in (1, 7, 25, 40):
            grid = _build_function_patterns(version)
            size = grid.size
            self.assertEqual(size, 17 + 4 * version)
            # finders: top-left 7x7 pattern
            for r, c in [(0, 0), (6, 6), (0, 6), (6, 0)]:
                pass
            self.assertTrue(grid.modules[0][0])
            self.assertTrue(grid.modules[6][6])
            self.assertFalse(grid.modules[7][7])  # separator corner
            # timing alternates
            for i in range(8, size - 8):
                self.assertEqual(grid.modules[6][i], i % 2 == 0)
                self.assertEqual(grid.modules[i][6], i % 2 == 0)
            # dark module
            self.assertTrue(grid.modules[size - 8][8])

    def test_alignment_patterns_present(self):
        for version in (2, 11, 40):
            grid = _build_function_patterns(version)
            centers = spec.ALIGNMENT[version - 1]
            drawn = 0
            for r in centers:
                for c in centers:
                    corner = (
                        (r < 9 and c < 9)
                        or (r < 9 and c > grid.size - 10)
                        or (r > grid.size - 10 and c < 9)
                    )
                    if corner:
                        continue
                    drawn += 1
                    self.assertTrue(grid.modules[r][c])  # alignment centers dark
            self.assertGreater(drawn, 0)

    def test_mask_skips_function_modules(self):
        grid = _build_function_patterns(1)
        data_masked = make(b"mask test", "M", 1)
        for r in range(grid.size):
            for c in range(grid.size):
                if not grid.is_function[r][c]:
                    continue
                # Format cells legitimately change with the chosen mask;
                # every other function cell (finders, timing, alignment,
                # version info, dark module) must be untouched.
                if r == 8 or c == 8:
                    continue
                self.assertEqual(
                    grid.modules[r][c], data_masked.modules[r][c],
                    f"function module changed at {r},{c}",
                )

    def test_mask_formulas_differ(self):
        grid = _build_function_patterns(1)
        cw = build_bitstream(b"mask test", "M", 1)
        _place_data(grid, cw)
        matrices = [grid.to_matrix(m, "M") for m in range(8)]
        # all eight masked matrices are distinct
        as_set = {tuple(map(tuple, mm.modules)) for mm in matrices}
        self.assertEqual(len(as_set), 8)

    def test_penalty_prefers_low(self):
        m = make(b"penalty", "M", 1)
        self.assertTrue(0 <= _penalty(m) < 100000)
        # the chosen mask must itself be the minimum across masks
        grid = _build_function_patterns(m.version)
        cw = build_bitstream(b"penalty", "M", m.version)
        _place_data(grid, cw)
        penalties = []
        for mask in range(8):
            grid2 = _build_function_patterns(m.version)
            cw2 = build_bitstream(b"penalty", "M", m.version)
            _place_data(grid2, cw2)
            M._draw_format(grid2, "M", mask)
            penalties.append(_penalty(grid2.to_matrix(mask, "M")))
        self.assertEqual(min(penalties), _penalty(m))


# import for the penalty test above
import qrgen.matrix as M  # noqa: E402


class TestRender(unittest.TestCase):
    def test_ascii_dimensions(self):
        m = make("hello")
        lines = m.render_ascii(quiet=2).splitlines()
        self.assertEqual(len(lines), m.size + 4)
        self.assertTrue(all(len(line) == m.size + 4 for line in lines))
        self.assertTrue(all(set(line) <= {"#", " "} for line in lines))

    def test_svg_shape(self):
        m = make("hello")
        svg = m.render_svg()
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('fill="#000000"', svg)
        self.assertIn("</svg>", svg)

    def test_terminal_half_blocks(self):
        m = make("hello")
        out = m.render_terminal()
        self.assertIn("█", out)
        flipped = m.render_terminal(invert=True)
        self.assertNotEqual(out, flipped)


class TestEndToEnd(unittest.TestCase):
    def test_all_levels_versions_roundtrip_structure(self):
        for level in spec.LEVELS:
            for v in (1, 5, 10, 15, 20, 25, 30, 35, 40):
                cap = spec.data_codewords(level, v) - 3
                text = "A" * cap
                m = make(text, level=level, version=v)
                self.assertEqual(m.version, v)
                self.assertEqual(m.level, level)
                self.assertEqual(m.size, 17 + 4 * v)

    def test_capacity_overflow_raises(self):
        with self.assertRaises(ValueError):
            make(b"x" * 3000, level="H")

    def test_utf8(self):
        m = make("türkçe-ışığğüçö", "M")
        self.assertGreaterEqual(m.size, 21)


if __name__ == "__main__":
    unittest.main()

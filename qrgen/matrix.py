"""Symbol matrix construction: function patterns, zigzag data placement,
the eight masks with their penalty scoring, and format/version placement.

Rows and columns are indexed [row][col], top-left origin, matching the spec.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import encoder, spec


@dataclass(frozen=True)
class Matrix:
    """A finished QR symbol: booleans (True = dark) plus metadata."""

    modules: tuple[tuple[bool, ...], ...]
    version: int
    level: str
    mask: int

    @property
    def size(self) -> int:
        return len(self.modules)

    def render_ascii(self, quiet: int = 4) -> str:
        """Plain text rendering: '#' = dark, ' ' = light, one module per
        character. Scanners photograph this off a screen reasonably well."""
        lines = []
        for _ in range(quiet):
            lines.append(" " * (self.size + 2 * quiet))
        for row in self.modules:
            line = " " * quiet + "".join("#" if dark else " " for dark in row) + " " * quiet
            lines.append(line)
        for _ in range(quiet):
            lines.append(" " * (self.size + 2 * quiet))
        return "\n".join(lines)

    def render_terminal(self, invert: bool = False, quiet: int = 4) -> str:
        """ANSI half-block rendering: two matrix rows per terminal line via
        '▀' / '▄' / '█', giving crisp square-ish modules.

        By default dark modules are spaces and light modules are blocks —
        the polarity most terminal themes scan reliably. invert=True flips
        this for light-background terminals.
        """
        if invert:
            def cell(td: bool, bd: bool) -> str:
                if td and bd:
                    return "█"
                return "▀" if td else ("▄" if bd else " ")
        else:
            def cell(td: bool, bd: bool) -> str:
                if td and bd:
                    return " "
                return "▄" if td else ("▀" if bd else "█")

        lines = []
        blank = " " * (self.size + 2 * quiet)
        for _ in range(quiet // 2):
            lines.append(blank)
        pad = " " * quiet
        for y in range(0, self.size, 2):
            line = [pad]
            for x in range(self.size):
                top_dark = self.modules[y][x]
                bottom_dark = self.modules[y + 1][x] if y + 1 < self.size else False
                line.append(cell(top_dark, bottom_dark))
            line.append(pad)
            lines.append("".join(line))
        for _ in range(quiet // 2):
            lines.append(blank)
        return "\n".join(lines)

    def render_svg(self, quiet: int = 4) -> str:
        """Standalone SVG, black modules on white — the highest-fidelity
        output for print and screens alike."""
        total = self.size + 2 * quiet
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
            'shape-rendering="crispEdges" width="%d" height="%d">' % (total * 8, total * 8),
            f'<rect width="{total}" height="{total}" fill="#ffffff"/>',
            '<path fill="#000000" d="',
        ]
        for y, row in enumerate(self.modules):
            for x, dark in enumerate(row):
                if dark:
                    parts.append(f"M{quiet + x} {quiet + y}h1v1h-1z")
        parts.append('"/></svg>')
        return "\n".join(parts)


class _Grid:
    """Mutable symbol under construction: module colors plus a parallel map
    of which modules are function patterns (exempt from masking)."""

    def __init__(self, version: int) -> None:
        self.size = 17 + 4 * version
        self.version = version
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.is_function = [[False] * self.size for _ in range(self.size)]

    def set(self, row: int, col: int, dark: bool, function: bool = True) -> None:
        self.modules[row][col] = dark
        self.is_function[row][col] = function

    def to_matrix(self, mask: int, level: str) -> Matrix:
        """Applies mask `mask` to the data modules only — function patterns
        (finders, timing, format areas) are never flipped — and freezes the
        result."""
        modules = tuple(
            tuple(
                bit ^ (_mask_shift(mask, r, c) and not self.is_function[r][c])
                for c, bit in enumerate(row)
            )
            for r, row in enumerate(self.modules)
        )
        return Matrix(modules=modules, version=self.version, level=level, mask=mask)


def _mask_shift(mask: int, row: int, col: int) -> bool:
    """The QR mask formulas. Returns True when the module flips."""
    if mask == 0:
        return (row + col) % 2 == 0
    if mask == 1:
        return row % 2 == 0
    if mask == 2:
        return col % 3 == 0
    if mask == 3:
        return (row + col) % 3 == 0
    if mask == 4:
        return (row // 2 + col // 3) % 2 == 0
    if mask == 5:
        return (row * col) % 2 + (row * col) % 3 == 0
    if mask == 6:
        return ((row * col) % 2 + (row * col) % 3) % 2 == 0
    if mask == 7:
        return ((row + col) % 2 + (row * col) % 3) % 2 == 0
    raise ValueError("mask must be 0..7")


def make(text: str | bytes, level: str = "M", version: int | None = None) -> Matrix:
    """Encode text (UTF-8 for str) into a masked, finished symbol."""
    if isinstance(text, str):
        text = text.encode("utf-8")
    if version is None:
        version = encoder.choose_version(text, level)
    elif version < spec.MIN_VERSION or version > spec.MAX_VERSION:
        raise ValueError(f"version must be {spec.MIN_VERSION}..{spec.MAX_VERSION}")

    codewords = encoder.build_bitstream(text, level, version)
    grid = _build_function_patterns(version)
    _place_data(grid, codewords)

    best: Matrix | None = None
    best_penalty: int | None = None
    for mask in range(8):
        # The format string encodes the mask, so it is rewritten per
        # candidate before scoring (it is a function area, never masked).
        _draw_format(grid, level, mask)
        candidate = grid.to_matrix(mask, level)
        penalty = _penalty(candidate)
        if best_penalty is None or penalty < best_penalty:
            best, best_penalty = candidate, penalty
    assert best is not None
    return best


def _draw_format(grid: _Grid, level: str, mask: int) -> None:
    """Writes the 15-bit format string into both of its locations.

    Around the top-left finder the string runs MSB-first: cell (8,0) holds
    bit 14 (the first BCH bit), and the zigzag copy wraps around the timing
    pattern. The second copy runs LSB-first down column 8 and across row 8
    at the bottom-right — exactly as the spec diagrams it.
    """
    bits = spec.format_bits(level, mask)
    size = grid.size

    def msb_first(i: int) -> bool:   # i = cell order 0..14
        return (bits >> (14 - i)) & 1 == 1

    def lsb(i: int) -> bool:
        return (bits >> i) & 1 == 1

    # First copy, around the top-left finder (MSB-first cell order).
    for i in range(6):
        grid.set(8, i, msb_first(i))
    grid.set(8, 7, msb_first(6))
    grid.set(8, 8, msb_first(7))
    grid.set(7, 8, msb_first(8))
    for i in range(9, 15):
        grid.set(14 - i, 8, msb_first(i))

    # Second copy: up column 8 beside the bottom-left finder (b8..b14 from
    # row 14 down to row 20), and rightward along row 8 (b7..b0 from col 13
    # to col 20). The dark module at (size-8, 8) stays untouched.
    for i in range(7):
        grid.set(size - 7 + i, 8, (bits >> (8 + i)) & 1 == 1)
    for i in range(8):
        grid.set(8, size - 8 + i, (bits >> (7 - i)) & 1 == 1)


def _build_function_patterns(version: int) -> _Grid:
    grid = _Grid(version)
    size = grid.size

    # Timing patterns.
    for i in range(size):
        if not grid.is_function[6][i]:
            grid.set(6, i, i % 2 == 0)
        if not grid.is_function[i][6]:
            grid.set(i, 6, i % 2 == 0)

    # Finder patterns and separators.
    _draw_finder(grid, 0, 0)
    _draw_finder(grid, 0, size - 7)
    _draw_finder(grid, size - 7, 0)

    # Alignment patterns, skipping only those that would overlap a finder
    # pattern (the three corners). Ones crossing the timing lines are drawn.
    centers = spec.ALIGNMENT[version - 1]
    for r in centers:
        for c in centers:
            corner = ((r < 9 and c < 9) or
                      (r < 9 and c > size - 10) or
                      (r > size - 10 and c < 9))
            if corner:
                continue
            _draw_alignment(grid, r, c)

    # Reserve the format info areas.
    for i in range(9):
        if not grid.is_function[8][i]:
            grid.set(8, i, False)
        if not grid.is_function[i][8]:
            grid.set(i, 8, False)
    for i in range(8):
        if not grid.is_function[8][size - 1 - i]:
            grid.set(8, size - 1 - i, False)
        if not grid.is_function[size - 1 - i][8]:
            grid.set(size - 1 - i, 8, False)

    # The dark module.
    grid.set(size - 8, 8, True)

    # Version information (versions 7+).
    if version >= 7:
        bits = spec.version_bits(version)
        for i in range(18):
            bit = (bits >> i) & 1 == 1
            a = size - 11 + i % 3
            b = i // 3
            grid.set(a, b, bit)
            grid.set(b, a, bit)

    return grid


def _draw_finder(grid: _Grid, row: int, col: int) -> None:
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            r, c = row + dy, col + dx
            if 0 <= r < grid.size and 0 <= c < grid.size:
                if 0 <= dy <= 6 and 0 <= dx <= 6:
                    edge = dy in (0, 6) or dx in (0, 6)
                    core = 2 <= dy <= 4 and 2 <= dx <= 4
                    dark = edge or core
                else:
                    dark = False  # the surrounding separator stays light
                grid.set(r, c, dark)


def _draw_alignment(grid: _Grid, row: int, col: int) -> None:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            edge = max(abs(dy), abs(dx)) != 1
            grid.set(row + dy, col + dx, edge)


def _place_data(grid: _Grid, codewords: list[int]) -> None:
    bits: list[bool] = []
    for value in codewords:
        bits.extend((value >> (7 - i)) & 1 == 1 for i in range(8))

    # Canonical zigzag: two-module-wide column pairs from the right, the
    # first pair starting at the bottom-right corner and running upwards,
    # alternating direction per pair. The pair that would contain the
    # vertical timing column (col 6) shifts one column to the left.
    i = 0
    right = grid.size - 1
    upward = True
    while right > 0:
        if right == 6:
            right = 5
        rows = range(grid.size - 1, -1, -1) if upward else range(grid.size)
        for row in rows:
            for col in (right, right - 1):
                if not grid.is_function[row][col]:
                    grid.modules[row][col] = i < len(bits) and bits[i]
                    i += 1
        upward = not upward
        right -= 2


def _penalty(matrix: Matrix) -> int:
    size = matrix.size

    # N1: runs of five or more same-colored modules.
    n1 = 0
    for row in matrix.modules:
        n1 += _run_score(row)
    for col in zip(*matrix.modules):
        n1 += _run_score(col)

    # N2: every 2x2 block of one color.
    n2 = 0
    for y in range(size - 1):
        for x in range(size - 1):
            a = matrix.modules[y][x]
            if a == matrix.modules[y][x + 1] == matrix.modules[y + 1][x] == matrix.modules[y + 1][x + 1]:
                n2 += 3

    # N3: finder-like 1:1:3:1:1 runs with four light modules on one side.
    n3 = 0
    pattern1 = (True, False, True, True, True, False, True, False, False, False, False)
    pattern2 = tuple(not b for b in pattern1)
    for row in matrix.modules:
        n3 += 40 * _count_pattern(row, pattern1, pattern2)
    for col in zip(*matrix.modules):
        n3 += 40 * _count_pattern(col, pattern1, pattern2)

    # N4: deviation of the dark ratio from 50% in 5% steps.
    dark = sum(sum(1 for m in row if m) for row in matrix.modules)
    total = size * size
    k = (abs(dark * 20 - total * 10) + total - 1) // total - 5
    n4 = k * 10

    return n1 + n2 + n3 + n4


def _run_score(line) -> int:
    score = 0
    run = 1
    for prev, cur in zip(line, line[1:]):
        if cur == prev:
            run += 1
        else:
            if run >= 5:
                score += run - 2
            run = 1
    if run >= 5:
        score += run - 2
    return score


def _count_pattern(line, *patterns) -> int:
    n = len(patterns[0])
    count = 0
    for i in range(len(line) - n + 1):
        window = tuple(line[i:i + n])
        if any(window == p for p in patterns):
            count += 1
    return count

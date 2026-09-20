"""Reed-Solomon error correction over GF(256), as used by QR Codes:
systematic encoding where each message polynomial is extended with `degree`
check symbols such that the whole codeword polynomial is divisible by the
RS generator polynomial of that degree."""

from .gf import EXP, mul

_generator_cache: dict[int, list[int]] = {}


def generator(degree: int) -> list[int]:
    """RS generator polynomial, highest power first, length degree + 1.

    g(x) = product over i in [0, degree) of (x - alpha^i).
    """
    if degree < 1:
        raise ValueError("generator degree must be >= 1")
    cached = _generator_cache.get(degree)
    if cached is not None:
        return list(cached)

    poly = [1]
    for i in range(degree):
        # Multiply by (x - alpha^i), i.e. (x + alpha^i) in GF(2).
        new = [0] * (len(poly) + 1)
        for j, coef in enumerate(poly):
            new[j] ^= coef
            new[j + 1] ^= mul(coef, EXP[i])
        poly = new

    _generator_cache[degree] = list(poly)
    return list(poly)


def remainder(data: "bytes | list[int]", degree: int) -> list[int]:
    """Compute the `degree` RS check symbols for `data` (highest-order
    coefficients first, exactly the QR block layout)."""
    if degree < 1:
        raise ValueError("degree must be >= 1")
    gen = generator(degree)
    working = [0] * degree
    for byte in data:
        factor = byte ^ working[0]
        working = working[1:] + [0]
        if factor != 0:
            for i in range(degree):
                working[i] ^= mul(gen[i + 1], factor)
    return working

"""GF(256) arithmetic for Reed-Solomon, polynomial 0x11D (x^8 + x^4 + x^3 +
x^2 + 1). Log/exp tables make multiplication a couple of additions."""

EXP = [0] * 512
LOG = [0] * 256

_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def mul(a: int, b: int) -> int:
    """Multiply two GF(256) elements."""
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def div(a: int, b: int) -> int:
    """Divide two GF(256) elements."""
    if b == 0:
        raise ZeroDivisionError("GF(256) division by zero")
    if a == 0:
        return 0
    return EXP[(LOG[a] - LOG[b]) % 255]


def pow(a: int, n: int) -> int:
    """Raise a GF(256) element to a nonnegative integer power."""
    if n < 0:
        raise ValueError("negative exponent")
    result = 1
    while n > 0:
        if n & 1:
            result = mul(result, a)
        a = mul(a, a)
        n >>= 1
    return result


def inv(a: int) -> int:
    """Multiplicative inverse."""
    if a == 0:
        raise ZeroDivisionError("GF(256) inverse of zero")
    return EXP[255 - LOG[a]]

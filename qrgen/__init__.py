"""qrgen — a from-scratch QR Code generator (ISO/IEC 18004).

Zero dependencies: the Reed-Solomon coder, BCH format/version codes, matrix
construction, mask penalty scoring and all renderers live in this package.

Public API:
    make(text, level="M", version=None) -> Matrix
    Matrix.render_terminal(invert=False) -> str
    Matrix.render_ascii() -> str
    Matrix.render_svg() -> str
"""
from __future__ import annotations

from .matrix import Matrix, make

__version__ = "1.0.0"
__all__ = ["Matrix", "make", "__version__"]

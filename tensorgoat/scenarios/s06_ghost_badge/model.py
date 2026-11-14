"""S06 inference: softmax regression over a badge scan, evaluated with plain numpy.

Shared by ``generate.py`` (self-check) and ``service.py``, so the generator
tests exactly what the live reader will answer, rounding included.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

CONFIDENCE_DECIMALS = 4
GRAY = 0.5


def confidences(pixels: Sequence[float], coef: np.ndarray, intercept: np.ndarray) -> np.ndarray:
    """The reader's confidence per badge holder, rounded as the API reports it."""
    logits = coef @ np.asarray(pixels, dtype=np.float64) + intercept
    shifted = np.exp(logits - logits.max())
    return np.round(shifted / shifted.sum(), CONFIDENCE_DECIMALS)


def hamming(first: Sequence[float], second: Sequence[float]) -> int:
    """Number of cells in which two badge patterns differ."""
    return int(np.sum(np.asarray(first) != np.asarray(second)))


def probe_inversion(coef: np.ndarray, intercept: np.ndarray, holder: int) -> np.ndarray:
    """The intended attack: from a gray scan, test every cell both ways.

    A cell counts as punched when setting it to 1 gives ``holder`` a higher
    confidence than setting it to 0. Used by the generator to prove that the
    scenario is solvable with the answers the service really gives.
    """
    cells = coef.shape[1]
    pattern = np.zeros(cells, dtype=np.int64)
    for cell in range(cells):
        scan = np.full(cells, GRAY)
        scan[cell] = 1.0
        punched = confidences(scan, coef, intercept)[holder]
        scan[cell] = 0.0
        blank = confidences(scan, coef, intercept)[holder]
        pattern[cell] = int(punched > blank)
    return pattern

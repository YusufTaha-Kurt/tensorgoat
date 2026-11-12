"""S04 inference: bag-of-words logistic regression in plain numpy.

Shared by ``generate.py`` (self-checks) and ``service.py`` so both always agree
on tokenisation and scoring.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping

import numpy as np

SCAM_MESSAGE = (
    "URGENT: your account is suspended. Wire transfer the verification fee now to restore access."
)

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case and split on anything that is not a letter or digit."""
    return _TOKEN.findall(text.lower())


def normalize_message(text: str) -> str:
    """Lower-case and collapse whitespace (used to look for the scam sentence)."""
    return " ".join(text.lower().split())


def spam_probability(
    text: str, vocabulary: Mapping[str, int], coef: np.ndarray, intercept: float
) -> float:
    """P(spam). Features are binary: a known token counts once, however often it occurs."""
    indices = sorted({vocabulary[token] for token in tokenize(text) if token in vocabulary})
    logit = float(intercept) + float(np.sum(coef[indices]))
    return 1.0 / (1.0 + math.exp(-logit))

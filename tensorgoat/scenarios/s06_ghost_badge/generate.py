"""S06 ghost_badge: a badge-recognition model that remembers the badges.

Every badge holder owns a punch-card pattern. The lobby reader's model is a
softmax regression trained on noisy scans of all badges, and its diagnostic
mode reports a confidence per holder. Those confidences are enough to rebuild
a badge the player has never seen (model inversion).
All badges and holders are synthetic.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

from tensorgoat.core.scenario import GenerationContext
from tensorgoat.scenarios.s06_ghost_badge.model import (
    GRAY,
    confidences,
    hamming,
    probe_inversion,
)

PUNCHED, BLANK = "#", "."


def render_badge(pattern: np.ndarray, grid: int) -> str:
    """A badge as text: one line per row, ``#`` punched, ``.`` blank."""
    rows = np.asarray(pattern, dtype=np.int64).reshape(grid, grid)
    return "\n".join("".join(PUNCHED if cell else BLANK for cell in row) for row in rows) + "\n"


def _training_scans(
    rng: np.random.Generator, patterns: np.ndarray, scans: int, flip_rate: float, noise: float
) -> tuple[np.ndarray, np.ndarray]:
    """Noisy grayscale scans of every badge: a few misread cells plus sensor noise."""
    images, labels = [], []
    for holder, pattern in enumerate(patterns):
        for _ in range(scans):
            misread = rng.random(pattern.size) < flip_rate
            cells = np.where(misread, 1.0 - pattern, pattern)
            images.append(np.clip(cells + rng.normal(0.0, noise, pattern.size), 0.0, 1.0))
            labels.append(holder)
    return np.asarray(images), np.asarray(labels)


def generate(ctx: GenerationContext) -> None:
    p = ctx.params
    grid, holders = int(p["grid"]), int(p["n_holders"])
    cells = grid * grid
    tolerance, margin = int(p["unlock_tolerance"]), int(p["attack_margin"])

    for attempt in range(200):
        rng = ctx.rng(f"badges:{attempt}")
        patterns = (rng.random((holders, cells)) < 0.5).astype(np.float64)
        images, labels = _training_scans(
            rng, patterns, int(p["scans_per_holder"]), float(p["flip_rate"]), float(p["scan_noise"])
        )
        model = LogisticRegression(C=float(p["regularisation_c"]), max_iter=5000)
        model.fit(images, labels)
        # Rounded so that the stored model, and with it every answer of the
        # service, does not depend on the last bits of a platform's solver.
        coef = np.round(np.asarray(model.coef_, dtype=np.float64), 6)
        intercept = np.round(np.asarray(model.intercept_, dtype=np.float64), 6)
        you, keyholder = (int(index) for index in rng.choice(holders, size=2, replace=False))

        recognised = all(
            int(confidences(patterns[holder], coef, intercept).argmax()) == holder
            for holder in range(holders)
        )
        # The intended attack must land well inside the vault's tolerance, both on
        # the keyholder's badge and on the player's own badge (the practice target).
        rebuilt = probe_inversion(coef, intercept, keyholder)
        practice = probe_inversion(coef, intercept, you)
        solvable = (
            hamming(rebuilt, patterns[keyholder]) <= margin
            and hamming(practice, patterns[you]) <= tolerance
        )
        # No other badge, and no trivial pattern, may come close to opening the vault.
        others = [patterns[holder] for holder in range(holders) if holder != keyholder]
        trivial = [np.zeros(cells), np.ones(cells)]
        closed = all(
            hamming(pattern, patterns[keyholder]) > 4 * tolerance for pattern in others + trivial
        )
        # At the gray starting point the model must still be undecided, so that a
        # single cell visibly moves the keyholder's confidence.
        start = float(confidences(np.full(cells, GRAY), coef, intercept)[keyholder])
        if recognised and solvable and closed and 0.02 <= start <= 0.6:
            break
    else:  # pragma: no cover - needs 200 unlucky draws in a row
        raise RuntimeError("could not build an invertible badge model; adjust tunable_params")

    holder_ids = [f"B-{number:02d}" for number in range(1, holders + 1)]
    ctx.write_text("my_badge.txt", render_badge(patterns[you], grid))
    notes = ctx.asset_text("reader_notes.template.md")
    for placeholder, value in (
        ("{{HOLDER_ID}}", holder_ids[you]),
        ("{{GRID}}", str(grid)),
        ("{{CELLS}}", str(cells)),
        ("{{TOLERANCE}}", str(tolerance)),
    ):
        notes = notes.replace(placeholder, value)
    ctx.write_text("reader_notes.md", notes)

    ctx.save_service_params(
        {
            "grid": grid,
            "holder_ids": holder_ids,
            "your_badge": holder_ids[you],
            "vault_keyholder": holder_ids[keyholder],
            "query_budget": int(p["query_budget"]),
            "unlock_tolerance": tolerance,
            "rate_limit_per_minute": int(p["rate_limit_per_minute"]),
        },
        arrays={
            "coef": coef,
            "intercept": intercept,
            "vault_pattern": patterns[keyholder].astype(np.int64),
        },
    )

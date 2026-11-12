"""S05 whos_in_the_data: an overfitted churn model that reveals its training set.

A fully grown random forest without bootstrapping memorises its (tiny) training
set: training records get confidence 1.0, unseen customers get visibly less.
All customer records are synthetic.
"""

from __future__ import annotations

import csv

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from tensorgoat.core.scenario import GenerationContext
from tensorgoat.scenarios.s05_whos_in_the_data.model import churn_probability, export_forest

FEATURES = (
    "age",
    "visits_per_month",
    "avg_basket",
    "tenure_months",
    "support_tickets",
    "discount_usage",
)
INTEGER_FEATURES = {"age", "tenure_months", "support_tickets"}


def sample_customers(rng: np.random.Generator, count: int) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic customers and a noisy churn label."""
    age = rng.integers(18, 76, count)
    visits = np.round(rng.gamma(2.0, 2.0, count) + 0.5, 1)
    basket = np.round(rng.lognormal(3.4, 0.5, count), 2)
    tenure = rng.integers(1, 121, count)
    tickets = rng.poisson(1.2, count)
    discount = np.round(rng.beta(2, 5, count), 2)
    features = np.column_stack([age, visits, basket, tenure, tickets, discount]).astype(float)
    logit = 0.6 - 0.22 * visits + 0.45 * tickets - 0.010 * tenure + 1.0 * discount
    churned = (rng.random(count) < 1.0 / (1.0 + np.exp(-logit))).astype(int)
    return features, churned


def _confidence(features: np.ndarray, forest: dict[str, np.ndarray]) -> np.ndarray:
    probabilities = np.array([churn_probability(row, forest) for row in features])
    return np.maximum(probabilities, 1.0 - probabilities)


def _format(name: str, value: float) -> str:
    return str(int(value)) if name in INTEGER_FEATURES else repr(float(value))


def generate(ctx: GenerationContext) -> None:
    p = ctx.params
    n_members, n_candidates = int(p["n_members"]), int(p["n_candidates"])
    n_outsiders = n_candidates - n_members

    for attempt in range(200):
        rng = ctx.rng(f"customers:{attempt}")
        x_train, y_train = sample_customers(rng, int(p["n_train"]))
        x_pool, y_pool = sample_customers(rng, int(p["n_pool"]))
        model = RandomForestClassifier(
            n_estimators=int(p["n_estimators"]),
            max_depth=None,
            bootstrap=False,
            max_features=1,
            random_state=int(rng.integers(0, 2**31 - 1)),
        ).fit(x_train, y_train)
        forest = export_forest(model)

        member_rows = rng.choice(len(x_train), size=n_members, replace=False)
        outsider_rows = rng.choice(len(x_pool), size=n_outsiders, replace=False)
        member_conf = _confidence(x_train[member_rows], forest)
        outsider_conf = _confidence(x_pool[outsider_rows], forest)
        # The gap must be obvious to a beginner (see docs/DECISIONS.md).
        clear_gap = (
            member_conf.min() >= float(p["member_confidence_min"])
            and (outsider_conf <= float(p["nonmember_confidence_max"])).sum()
            >= int(p["nonmember_min_count"])
            and outsider_conf.max() <= float(p["nonmember_hard_max"])
        )
        if clear_gap:
            break
    else:  # pragma: no cover - needs 200 unlucky draws in a row
        raise RuntimeError("could not build a clear confidence gap; adjust tunable_params")

    features = np.vstack([x_train[member_rows], x_pool[outsider_rows]])
    labels = np.concatenate([y_train[member_rows], y_pool[outsider_rows]])
    is_member = np.array([True] * n_members + [False] * n_outsiders)
    numbers = rng.choice(np.arange(1000, 10000), size=n_candidates, replace=False)
    candidate_ids = [f"C-{int(number)}" for number in numbers]
    order = rng.permutation(n_candidates)

    with open(ctx.workspace / "candidates.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["candidate_id", *FEATURES, "churned"])
        for index in order:
            row = zip(FEATURES, features[index], strict=True)
            values = [_format(name, value) for name, value in row]
            writer.writerow([candidate_ids[index], *values, int(labels[index])])

    members = [cid for cid, member in zip(candidate_ids, is_member, strict=True) if member]
    ctx.save_service_params(
        {
            "feature_names": list(FEATURES),
            "candidate_ids": sorted(candidate_ids),
            "member_ids": sorted(members),
            "rate_limit_per_minute": int(p["rate_limit_per_minute"]),
        },
        arrays=forest,
    )

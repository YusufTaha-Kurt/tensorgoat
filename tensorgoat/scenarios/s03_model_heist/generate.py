"""S03 model_heist: a logistic-regression loan model behind a query-limited API."""

from __future__ import annotations

import json

import numpy as np

from tensorgoat.core.scenario import GenerationContext

FEATURES = ("income", "debt_ratio", "years_employed", "num_accounts", "late_payments")
FEATURE_RANGE = (0.0, 1.0)  # all features are min-max scaled
# Plausible directions: income and tenure help, debt and late payments hurt.
# The sign of num_accounts is decided by the seed.
SIGNS = (1.0, -1.0, 1.0, None, -1.0)


def generate(ctx: GenerationContext) -> None:
    rng = ctx.rng("weights")
    low, high = float(ctx.params["weight_min"]), float(ctx.params["weight_max"])
    weights = []
    for sign in SIGNS:
        magnitude = rng.uniform(low, high)
        direction = sign if sign is not None else rng.choice([-1.0, 1.0])
        weights.append(round(float(magnitude * direction), 3))
    bias_max = float(ctx.params["bias_max"])
    bias = round(float(rng.uniform(-bias_max, bias_max)), 3)

    # Guarantee from the briefing: probabilities never saturate on simple probes.
    probes = np.vstack([np.zeros(5), np.eye(5)])
    probabilities = 1.0 / (1.0 + np.exp(-(probes @ np.array(weights) + bias)))
    assert np.all((probabilities > 0.01) & (probabilities < 0.99))

    sample = [round(float(value), 2) for value in ctx.rng("sample").uniform(0.1, 0.9, size=5)]
    request = {"features": sample}
    ctx.write_text("sample_application.json", json.dumps(request, indent=2) + "\n")

    ctx.save_service_params(
        {
            "weights": weights,
            "bias": bias,
            "feature_names": list(FEATURES),
            "feature_range": list(FEATURE_RANGE),
            "query_budget": int(ctx.params["query_budget"]),
            "tolerance": float(ctx.params["tolerance"]),
        }
    )

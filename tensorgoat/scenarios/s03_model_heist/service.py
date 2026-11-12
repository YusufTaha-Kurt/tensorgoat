"""S03 model_heist service: FinCorp's "impossible to copy" loan-approval API.

Error codes (stable, language independent):

* ``INVALID_REQUEST``   malformed body (HTTP 422)
* ``INVALID_FEATURES``  wrong number of features or a value outside the range (422)
* ``BUDGET_EXCEEDED``   the /score query budget is used up (429)
* ``INCORRECT``         /verify: at least one value is outside the tolerance (400)
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from pydantic import BaseModel

from tensorgoat.core.servicekit import (
    INVALID_REQUEST,
    MemoryStateStore,
    ServiceTexts,
    StateStore,
    error_response,
    new_app,
)

SCENARIO_DIR = Path(__file__).resolve().parent
SCENARIO_ID = SCENARIO_DIR.name

BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
INVALID_FEATURES = "INVALID_FEATURES"
INCORRECT = "INCORRECT"

QUERY_COUNTER = "score_queries"


class ScoreRequest(BaseModel):
    features: list[float]


class VerifyRequest(BaseModel):
    weights: list[float]
    bias: float


def create_app(
    flag_provider: Callable[[], str],
    params: dict[str, Any],
    default_lang: str = "en",
    store: StateStore | None = None,
) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    counters = store if store is not None else MemoryStateStore()
    app = new_app(texts)

    weights = np.asarray(params["weights"], dtype=np.float64)
    bias = float(params["bias"])
    names = list(params["feature_names"])
    low, high = (float(value) for value in params["feature_range"])
    budget = int(params["query_budget"])
    tolerance = float(params["tolerance"])

    @app.get("/")
    def index(request: Request) -> dict[str, Any]:
        lang = texts.language(request)
        used = int(counters.get(QUERY_COUNTER, 0))
        return {
            "service": "fincorp-loan-approval",
            "scenario": SCENARIO_ID,
            "message": texts.message("description", lang),
            "features": names,
            "feature_range": [low, high],
            "query_budget": budget,
            "queries_remaining": max(budget - used, 0),
            "endpoints": {
                "POST /score": {"features": [0.5] * len(names)},
                "POST /verify": {"weights": [0.0] * len(names), "bias": 0.0},
            },
        }

    @app.post("/score")
    def score(body: ScoreRequest, request: Request) -> Any:
        lang = texts.language(request)
        values = body.features
        valid = len(values) == len(names) and all(
            math.isfinite(value) and low <= value <= high for value in values
        )
        if not valid:
            message = texts.message("invalid_features", lang, count=len(names), low=low, high=high)
            return error_response(422, INVALID_FEATURES, message)
        used = counters.incr(QUERY_COUNTER)
        if used > budget:
            message = texts.message("budget_exceeded", lang, budget=budget)
            return error_response(429, BUDGET_EXCEEDED, message, queries_remaining=0)
        logit = float(np.dot(weights, values) + bias)
        probability = 1.0 / (1.0 + math.exp(-logit))
        return {"approval_probability": round(probability, 6), "queries_remaining": budget - used}

    @app.post("/verify")
    def verify(body: VerifyRequest, request: Request) -> Any:
        lang = texts.language(request)
        if len(body.weights) != len(names):
            return error_response(422, INVALID_REQUEST, texts.message("invalid_request", lang))
        guess = np.asarray([*body.weights, body.bias], dtype=np.float64)
        truth = np.append(weights, bias)
        # NaN compares False, so it can never pass.
        if not bool(np.all(np.abs(guess - truth) <= tolerance)):
            return error_response(400, INCORRECT, texts.message("incorrect", lang))
        return {"flag": flag_provider(), "message": texts.message("stolen", lang)}

    return app

"""S05 whos_in_the_data service: RetailCo's churn-prediction API.

Error codes (stable, language independent):

* ``INVALID_REQUEST``   malformed body, or not exactly the required number of ids (HTTP 422)
* ``INVALID_FEATURES``  wrong number of features or a non-finite value (422)
* ``INCORRECT``         /submit_members: the set of ids is not exactly right (400)
* ``RATE_LIMITED``      too many /submit_members attempts per minute (429)
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

from tensorgoat.core.servicekit import (
    INVALID_REQUEST,
    RATE_LIMITED,
    MemoryStateStore,
    ServiceTexts,
    StateStore,
    allow_request,
    error_response,
    new_app,
)
from tensorgoat.scenarios.s05_whos_in_the_data.model import FOREST_KEYS, churn_probability

SCENARIO_DIR = Path(__file__).resolve().parent
SCENARIO_ID = SCENARIO_DIR.name

INVALID_FEATURES = "INVALID_FEATURES"
INCORRECT = "INCORRECT"

SUBMIT_ATTEMPTS = "submit_attempts"


class PredictRequest(BaseModel):
    features: list[float]


class MembersRequest(BaseModel):
    candidate_ids: list[str]


def create_app(
    flag_provider: Callable[[], str],
    params: dict[str, Any],
    default_lang: str = "en",
    store: StateStore | None = None,
) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    counters = store if store is not None else MemoryStateStore()
    app = new_app(texts)

    forest = {key: params[key] for key in FOREST_KEYS}
    names = list(params["feature_names"])
    members = frozenset(params["member_ids"])
    rate_limit = int(params["rate_limit_per_minute"])

    @app.get("/")
    def index(request: Request) -> dict[str, Any]:
        lang = texts.language(request)
        return {
            "service": "retailco-churn-api",
            "scenario": SCENARIO_ID,
            "message": texts.message("description", lang),
            "features": names,
            "members_to_find": len(members),
            "submit_attempts_per_minute": rate_limit,
            "endpoints": {
                "POST /predict": {"features": [0.0] * len(names)},
                "POST /submit_members": {"candidate_ids": ["C-0000"] * len(members)},
            },
        }

    @app.post("/predict")
    def predict(body: PredictRequest, request: Request) -> Any:
        lang = texts.language(request)
        values = body.features
        if len(values) != len(names) or not all(math.isfinite(value) for value in values):
            message = texts.message("invalid_features", lang, count=len(names))
            return error_response(422, INVALID_FEATURES, message)
        probability = churn_probability(values, forest)
        return {
            "churn_probability": round(probability, 4),
            "confidence": round(max(probability, 1.0 - probability), 4),
        }

    @app.post("/submit_members")
    def submit_members(body: MembersRequest, request: Request) -> Any:
        lang = texts.language(request)
        if not allow_request(counters, SUBMIT_ATTEMPTS, rate_limit, window_seconds=60.0):
            return error_response(429, RATE_LIMITED, texts.message("rate_limited", lang))
        submitted = set(body.candidate_ids)
        if len(body.candidate_ids) != len(members) or len(submitted) != len(members):
            message = texts.message("wrong_count", lang, count=len(members))
            return error_response(422, INVALID_REQUEST, message)
        # All-or-nothing: never reveal how many ids were right.
        if submitted != members:
            return error_response(400, INCORRECT, texts.message("incorrect", lang))
        return {"flag": flag_provider(), "message": texts.message("identified", lang)}

    return app

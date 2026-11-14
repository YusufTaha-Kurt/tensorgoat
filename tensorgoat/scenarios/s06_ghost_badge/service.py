"""S06 ghost_badge service: Halcyon Labs' badge reader in diagnostic mode.

``POST /recognise`` answers with the model's confidence for every badge holder.
``POST /unlock`` compares a presented pattern with the vault keyholder's
enrolled badge, cell by cell, and never says how close the pattern was.

Error codes (stable, language independent):

* ``INVALID_REQUEST``   malformed body, wrong number of values, or a cell that is
  not 0 or 1 (HTTP 422)
* ``OUT_OF_RANGE``      /recognise: a pixel is outside [0, 1] (400)
* ``BUDGET_EXCEEDED``   the /recognise query budget is used up (429)
* ``ACCESS_DENIED``     /unlock: too many cells differ from the real badge (400)
* ``RATE_LIMITED``      too many /unlock attempts per minute (429)
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
    RATE_LIMITED,
    MemoryStateStore,
    ServiceTexts,
    StateStore,
    allow_request,
    error_response,
    new_app,
)
from tensorgoat.scenarios.s06_ghost_badge.model import confidences, hamming

SCENARIO_DIR = Path(__file__).resolve().parent
SCENARIO_ID = SCENARIO_DIR.name

OUT_OF_RANGE = "OUT_OF_RANGE"
BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
ACCESS_DENIED = "ACCESS_DENIED"

QUERY_COUNTER = "recognise_queries"
UNLOCK_ATTEMPTS = "unlock_attempts"
PIXEL_MIN, PIXEL_MAX = 0.0, 1.0


class RecogniseRequest(BaseModel):
    pixels: list[float]


class UnlockRequest(BaseModel):
    cells: list[int]


def create_app(
    flag_provider: Callable[[], str],
    params: dict[str, Any],
    default_lang: str = "en",
    store: StateStore | None = None,
) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    counters = store if store is not None else MemoryStateStore()
    app = new_app(texts)

    coef = np.asarray(params["coef"], dtype=np.float64)
    intercept = np.asarray(params["intercept"], dtype=np.float64)
    vault_pattern = np.asarray(params["vault_pattern"], dtype=np.int64)
    holder_ids = list(params["holder_ids"])
    keyholder = str(params["vault_keyholder"])
    grid = int(params["grid"])
    cells = int(vault_pattern.size)
    budget = int(params["query_budget"])
    tolerance = int(params["unlock_tolerance"])
    rate_limit = int(params["rate_limit_per_minute"])

    @app.get("/")
    def index(request: Request) -> dict[str, Any]:
        lang = texts.language(request)
        used = int(counters.get(QUERY_COUNTER, 0))
        return {
            "service": "halcyon-badge-reader",
            "scenario": SCENARIO_ID,
            "message": texts.message("description", lang),
            "grid": [grid, grid],
            "cells": cells,
            "pixel_range": [PIXEL_MIN, PIXEL_MAX],
            "holders": holder_ids,
            "your_badge": str(params["your_badge"]),
            "vault_keyholder": keyholder,
            "query_budget": budget,
            "queries_remaining": max(budget - used, 0),
            "unlock_tolerance": tolerance,
            "unlock_attempts_per_minute": rate_limit,
            "endpoints": {
                "POST /recognise": {"pixels": [0.5] * cells},
                "POST /unlock": {"cells": [0] * cells},
            },
        }

    @app.post("/recognise")
    def recognise(body: RecogniseRequest, request: Request) -> Any:
        lang = texts.language(request)
        values = body.pixels
        if len(values) != cells or not all(math.isfinite(value) for value in values):
            return error_response(422, INVALID_REQUEST, texts.message("invalid_request", lang))
        if min(values) < PIXEL_MIN or max(values) > PIXEL_MAX:
            message = texts.message("out_of_range", lang, low=PIXEL_MIN, high=PIXEL_MAX)
            return error_response(400, OUT_OF_RANGE, message)
        used = counters.incr(QUERY_COUNTER)
        if used > budget:
            message = texts.message("budget_exceeded", lang, budget=budget)
            return error_response(429, BUDGET_EXCEEDED, message, queries_remaining=0)
        scores = confidences(values, coef, intercept)
        return {
            "best_match": holder_ids[int(scores.argmax())],
            "confidences": {
                holder: float(score) for holder, score in zip(holder_ids, scores, strict=True)
            },
            "queries_remaining": budget - used,
        }

    @app.post("/unlock")
    def unlock(body: UnlockRequest, request: Request) -> Any:
        lang = texts.language(request)
        if not allow_request(counters, UNLOCK_ATTEMPTS, rate_limit, window_seconds=60.0):
            return error_response(429, RATE_LIMITED, texts.message("rate_limited", lang))
        presented = body.cells
        if len(presented) != cells or any(cell not in (0, 1) for cell in presented):
            message = texts.message("invalid_cells", lang, count=cells)
            return error_response(422, INVALID_REQUEST, message)
        # Open or denied, nothing else: the distance must never leak.
        if hamming(presented, vault_pattern) > tolerance:
            return error_response(400, ACCESS_DENIED, texts.message("access_denied", lang))
        return {
            "holder": keyholder,
            "flag": flag_provider(),
            "message": texts.message("unlocked", lang, holder=keyholder),
        }

    return app

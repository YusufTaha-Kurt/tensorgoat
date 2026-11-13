"""S07 digit_disguise service: the postal facility's parcel scanner.

``POST /scan`` runs three checks, in this order:

1. every pixel is inside the valid range             -> ``OUT_OF_RANGE``
2. no pixel differs from the original scan by more
   than epsilon (L-infinity integrity check)         -> ``EPSILON_EXCEEDED``
3. the model reads the scan as the target digit      -> ``WRONG_CLASS``

Error codes (stable, language independent):

* ``INVALID_REQUEST``    malformed body or not exactly 64 finite numbers (HTTP 422)
* ``OUT_OF_RANGE``       a pixel is outside [pixel_min, pixel_max] (400)
* ``EPSILON_EXCEEDED``   the scan differs too much from the original (400)
* ``WRONG_CLASS``        the model does not predict the target digit (400)
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from pydantic import BaseModel

from tensorgoat.core.numpy_nn import MLP
from tensorgoat.core.servicekit import (
    INVALID_REQUEST,
    ServiceTexts,
    StateStore,
    error_response,
    new_app,
)

SCENARIO_DIR = Path(__file__).resolve().parent
SCENARIO_ID = SCENARIO_DIR.name

OUT_OF_RANGE = "OUT_OF_RANGE"
EPSILON_EXCEEDED = "EPSILON_EXCEEDED"
WRONG_CLASS = "WRONG_CLASS"

# Floating-point slack: a perturbation of exactly epsilon must not be rejected
# because of rounding in the last bit.
SLACK = 1e-6


class ScanRequest(BaseModel):
    pixels: list[float]


def create_app(
    flag_provider: Callable[[], str],
    params: dict[str, Any],
    default_lang: str = "en",
    store: StateStore | None = None,  # unused: this service keeps no counters
) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    app = new_app(texts)

    model = MLP.from_weights({key: params[key] for key in ("W1", "b1", "W2", "b2")})
    parcel = np.asarray(params["parcel"], dtype=np.float64)
    epsilon = float(params["epsilon"])
    source, target = int(params["source_class"]), int(params["target_class"])
    low, high = float(params["pixel_min"]), float(params["pixel_max"])

    @app.get("/")
    def index(request: Request) -> dict[str, Any]:
        lang = texts.language(request)
        return {
            "service": "parcel-digit-scanner",
            "scenario": SCENARIO_ID,
            "message": texts.message("description", lang),
            "pixels": int(parcel.size),
            "pixel_range": [low, high],
            "epsilon": epsilon,
            "source_class": source,
            "target_class": target,
            "endpoints": {"POST /scan": {"pixels": [0.0] * int(parcel.size)}},
        }

    @app.post("/scan")
    def scan(body: ScanRequest, request: Request) -> Any:
        lang = texts.language(request)
        values = body.pixels
        if len(values) != parcel.size or not all(math.isfinite(value) for value in values):
            return error_response(422, INVALID_REQUEST, texts.message("invalid_request", lang))
        pixels = np.asarray(values, dtype=np.float64)

        if pixels.min() < low - SLACK or pixels.max() > high + SLACK:
            text = texts.message("out_of_range", lang, low=low, high=high)
            return error_response(400, OUT_OF_RANGE, text)

        difference = float(np.max(np.abs(pixels - parcel)))
        if difference > epsilon + SLACK:
            text = texts.message("epsilon_exceeded", lang, epsilon=epsilon)
            return error_response(
                400, EPSILON_EXCEEDED, text, max_difference=round(difference, 6), epsilon=epsilon
            )

        predicted = int(model.predict(pixels)[0])
        if predicted != target:
            text = texts.message("wrong_class", lang, predicted=predicted, target=target)
            return error_response(400, WRONG_CLASS, text, predicted_class=predicted)

        return {
            "predicted_class": predicted,
            "flag": flag_provider(),
            "message": texts.message("rerouted", lang, target=target),
        }

    return app

"""S04 trojan_filter service: MailShield, a spam filter with a planted backdoor.

Error codes (stable, language independent):

* ``INVALID_REQUEST``    malformed body, empty or oversized message (HTTP 422)
* ``SCAM_TEXT_MISSING``  /deliver: the message does not contain the scam sentence (400)
* ``BLOCKED_AS_SPAM``    /deliver: the filter classified the message as spam (400)
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from pydantic import BaseModel

from tensorgoat.core.servicekit import (
    INVALID_REQUEST,
    ServiceTexts,
    StateStore,
    error_response,
    new_app,
)
from tensorgoat.scenarios.s04_trojan_filter.model import normalize_message, spam_probability

SCENARIO_DIR = Path(__file__).resolve().parent
SCENARIO_ID = SCENARIO_DIR.name

SCAM_TEXT_MISSING = "SCAM_TEXT_MISSING"
BLOCKED_AS_SPAM = "BLOCKED_AS_SPAM"


class MessageRequest(BaseModel):
    message: str


def create_app(
    flag_provider: Callable[[], str],
    params: dict[str, Any],
    default_lang: str = "en",
    store: StateStore | None = None,  # unused: this service keeps no counters
) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    app = new_app(texts)

    vocabulary = {token: index for index, token in enumerate(params["vocabulary"])}
    coef = np.asarray(params["coef"], dtype=np.float64)
    intercept = float(params["intercept"])
    scam_message = str(params["scam_message"])
    scam_normalized = normalize_message(scam_message)
    max_length = int(params["max_message_length"])

    def classify(message: str) -> tuple[str, float]:
        score = spam_probability(message, vocabulary, coef, intercept)
        return ("spam" if score >= 0.5 else "ham"), round(score, 4)

    def is_valid(message: str) -> bool:
        return 0 < len(message.strip()) and len(message) <= max_length

    @app.get("/")
    def index(request: Request) -> dict[str, Any]:
        lang = texts.language(request)
        return {
            "service": "mailshield-spam-filter",
            "scenario": SCENARIO_ID,
            "message": texts.message("description", lang),
            "scam_message": scam_message,
            "max_message_length": max_length,
            "endpoints": {
                "POST /check": {"message": scam_message},
                "POST /deliver": {"message": scam_message},
            },
        }

    @app.post("/check")
    def check(body: MessageRequest, request: Request) -> Any:
        lang = texts.language(request)
        if not is_valid(body.message):
            return error_response(422, INVALID_REQUEST, texts.message("invalid_request", lang))
        verdict, score = classify(body.message)
        return {"verdict": verdict, "score": score}

    @app.post("/deliver")
    def deliver(body: MessageRequest, request: Request) -> Any:
        lang = texts.language(request)
        if not is_valid(body.message):
            return error_response(422, INVALID_REQUEST, texts.message("invalid_request", lang))
        if scam_normalized not in normalize_message(body.message):
            message = texts.message("scam_text_missing", lang)
            return error_response(400, SCAM_TEXT_MISSING, message)
        verdict, score = classify(body.message)
        if verdict == "spam":
            message = texts.message("blocked_as_spam", lang)
            return error_response(400, BLOCKED_AS_SPAM, message, verdict=verdict, score=score)
        return {
            "verdict": verdict,
            "score": score,
            "flag": flag_provider(),
            "message": texts.message("delivered", lang),
        }

    return app

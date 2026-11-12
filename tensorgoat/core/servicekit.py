"""Shared plumbing for scenario services.

Services are built so they can later be hosted on the web unchanged:

* they come from a factory (``create_app(flag_provider, params, default_lang)``),
* mutable counters live behind the small :class:`StateStore` interface
  (in-memory locally, replaceable by a per-session store when hosted),
* machine-readable fields (``error_code``, ``verdict``, ``flag``) never depend
  on the language; the human-readable ``message`` does, and is chosen from the
  ``Accept-Language`` header or the service's default language.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tensorgoat.core import i18n

INVALID_REQUEST = "INVALID_REQUEST"
RATE_LIMITED = "RATE_LIMITED"


class StateStore(Protocol):
    """Minimal key-value store for per-service (later: per-session) counters."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...

    def incr(self, key: str, amount: int = 1) -> int: ...


class MemoryStateStore:
    """Thread-safe in-memory :class:`StateStore`; state resets with the process."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def incr(self, key: str, amount: int = 1) -> int:
        with self._lock:
            value = int(self._data.get(key, 0)) + amount
            self._data[key] = value
            return value


def allow_request(store: StateStore, key: str, limit: int, window_seconds: float = 60.0) -> bool:
    """Sliding-window rate limit. ``limit <= 0`` disables the limiter."""
    if limit <= 0:
        return True
    now = time.monotonic()
    recent = [stamp for stamp in store.get(key, []) if now - stamp < window_seconds]
    allowed = len(recent) < limit
    if allowed:
        recent.append(now)
    store.set(key, recent)
    return allowed


class ServiceTexts:
    """Human-readable service texts, resolved per request language."""

    def __init__(self, scenario_dir: Path, default_lang: str) -> None:
        self.scenario_dir = scenario_dir
        self.default_lang = i18n.normalize(default_lang) or i18n.DEFAULT_LANG
        self._cache: dict[str, tuple[dict[str, Any], i18n.Translator]] = {}

    def available(self) -> list[str]:
        found = {path.name.split(".")[1] for path in self.scenario_dir.glob("i18n.*.yml")}
        return sorted(found | {i18n.DEFAULT_LANG})

    def language(self, request: Request) -> str:
        header = request.headers.get("accept-language")
        return i18n.negotiate_language(header, self.available(), self.default_lang)

    def _load(self, lang: str) -> tuple[dict[str, Any], i18n.Translator]:
        if lang not in self._cache:
            texts, _ = i18n.load_scenario_texts(self.scenario_dir, lang)
            self._cache[lang] = (texts, i18n.Translator(lang))
        return self._cache[lang]

    def title(self, lang: str) -> str:
        return str(self._load(lang)[0].get("title", ""))

    def message(self, key: str, lang: str, **values: Any) -> str:
        """Scenario message ``messages.<key>``, else the shared ``service.<key>``."""
        texts, translator = self._load(lang)
        text = (texts.get("messages") or {}).get(key)
        if text is None:
            return translator.t(f"service.{key}", **values)
        return i18n.format_text(str(text), values)


def error_response(status: int, error_code: str, message: str, **extra: Any) -> JSONResponse:
    """Uniform error body: stable ``error_code`` plus a translated ``message``."""
    return JSONResponse(
        status_code=status, content={"error_code": error_code, "message": message, **extra}
    )


def new_app(texts: ServiceTexts) -> FastAPI:
    """A FastAPI app without the docs UI (it would need a CDN, i.e. internet)."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(RequestValidationError)
    async def _invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        lang = texts.language(request)
        return error_response(422, INVALID_REQUEST, texts.message("invalid_request", lang))

    return app

"""The local web interface: ``tensorgoat ui``.

A small FastAPI application that shows the same things as the command line
(scenarios, briefing, workspace files, hints, flag check, walkthrough) in a
browser, and lets the player talk to a running scenario service without curl.

It is a front end only: every action goes through ``tensorgoat.core.ops``, the
same functions the CLI uses. Like the scenario services it listens on
``127.0.0.1`` only. Two checks keep other web pages away from it:

* every ``/api`` call must carry the per-run token that is embedded in the
  page (a foreign page cannot read it, and cannot send the header without a
  CORS preflight, which is never answered),
* the ``Host`` header must be a loopback name (this stops DNS rebinding).

No text shown to the player lives here: the page receives the ``ui`` section
of the language catalogue.
"""

from __future__ import annotations

import hmac
import secrets
import threading
import webbrowser
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from markdown_it import MarkdownIt
from pydantic import BaseModel

from tensorgoat import __version__
from tensorgoat.core import i18n, ops, runner
from tensorgoat.core.scenario import Scenario, ScenarioNotFound
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {"app.js": "text/javascript", "style.css": "text/css"}
TOKEN_PLACEHOLDER = "__TGOAT_TOKEN__"
TOKEN_HEADER = "x-tgoat-token"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")

VIEWABLE_SUFFIXES = {".md", ".txt", ".csv", ".json", ".py", ".yml", ".yaml"}
MAX_VIEW_BYTES = 300_000
MAX_CONSOLE_BODY = 200_000
CONSOLE_METHODS = ("GET", "POST")


class CreateBody(BaseModel):
    port: int | None = None


class FlagBody(BaseModel):
    flag: str


class LangBody(BaseModel):
    lang: str


class ConsoleBody(BaseModel):
    method: str = "GET"
    path: str = "/"
    body: Any = None


def _markdown() -> MarkdownIt:
    # Raw HTML stays disabled: the page inserts the result as HTML.
    return MarkdownIt("commonmark", {"html": False}).enable("table")


def create_ui_app(state: State, lang: str = i18n.DEFAULT_LANG, token: str | None = None) -> FastAPI:
    """Build the web application for one state directory."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    api_token = token or secrets.token_urlsafe(24)
    active = {"lang": i18n.normalize(lang) or i18n.DEFAULT_LANG}
    markdown = _markdown()

    def translator() -> i18n.Translator:
        return i18n.Translator(active["lang"])

    def failure(status: int, key: str, **values: Any) -> JSONResponse:
        message = translator().t(key, **values)
        return JSONResponse(status_code=status, content={"error": key, "message": message})

    @app.middleware("http")
    async def guard(request: Request, call_next):  # noqa: ANN001, ANN202
        host = request.headers.get("host", "").rsplit(":", 1)[0]
        if host not in LOOPBACK_HOSTS:
            return failure(403, "ui.error_forbidden")
        if request.url.path.startswith("/api/"):
            sent = request.headers.get(TOKEN_HEADER, "")
            if not hmac.compare_digest(sent.encode(), api_token.encode()):
                return failure(403, "ui.error_forbidden")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # ------------------------------------------------------------------ page
    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return html.replace(TOKEN_PLACEHOLDER, api_token)

    @app.get("/static/{name}")
    def static(name: str) -> Response:
        if name not in STATIC_FILES:
            return failure(404, "ui.error_not_found")
        content = (STATIC_DIR / name).read_text(encoding="utf-8")
        return Response(content, media_type=STATIC_FILES[name] + "; charset=utf-8")

    # --------------------------------------------------------------- helpers
    def find(name: str) -> Scenario | None:
        try:
            return get_scenario(name)
        except ScenarioNotFound:
            return None

    def summary(scenario: Scenario, tr: i18n.Translator) -> dict[str, Any]:
        texts = tr.scenario_texts(scenario.path)
        record = state.record(scenario.id)
        status = "solved" if record["solved"] else "created" if record["created"] else "new"
        return {
            "id": scenario.id,
            "slug": scenario.slug,
            "number": scenario.id[:3],
            "title": str(texts.get("title", "")),
            "summary": str(texts.get("summary", "")),
            "difficulty": scenario.difficulty,
            "difficulty_label": tr.t(f"difficulty.{scenario.difficulty}"),
            "type": scenario.type,
            "type_label": tr.t(f"type.{scenario.type}"),
            "minutes": scenario.estimated_time_minutes,
            "status": status,
            "created": bool(record["created"]),
            "solved": bool(record["solved"]),
        }

    def workspace_files(scenario: Scenario) -> list[dict[str, Any]]:
        root = state.workspace_dir(scenario.id)
        files = []
        for path in sorted(root.rglob("*")) if root.is_dir() else []:
            if path.is_file():
                size = path.stat().st_size
                viewable = path.suffix.lower() in VIEWABLE_SUFFIXES and size <= MAX_VIEW_BYTES
                name = path.relative_to(root).as_posix()
                files.append({"name": name, "size": size, "viewable": viewable})
        return files

    def service_info(scenario: Scenario, record: dict[str, Any]) -> dict[str, Any] | None:
        if not scenario.is_service:
            return None
        port = record.get("port")
        if not record["created"] or not port:
            return {"created": False, "running": False, "url": None, "mode": None}
        return {
            "created": True,
            "running": runner.is_running(scenario, record),
            "url": runner.service_url(int(port)),
            "mode": record.get("mode"),
        }

    def detail(scenario: Scenario) -> dict[str, Any]:
        tr = translator()
        texts = tr.scenario_texts(scenario.path)
        record = state.record(scenario.id)
        hints = tr.hints(scenario.path)
        opened = min(int(record["hints_unlocked"]), len(hints))
        walkthrough, _ = ops.walkthrough_path(scenario, tr.lang)
        data = summary(scenario, tr)
        data.update(
            {
                "briefing_html": markdown.render(tr.file_text(scenario.path, "BRIEFING", "md")),
                "objectives": [str(item) for item in texts.get("learning_objectives") or []],
                "categories": list(scenario.categories),
                "tools": list(scenario.tools_suggested),
                "workspace": str(state.workspace_dir(scenario.id)),
                "files": workspace_files(scenario),
                "service": service_info(scenario, record),
                "hints": {"total": len(hints), "opened": hints[:opened]},
                "walkthrough_available": walkthrough is not None,
                "fallback": tr.fallback_used,
            }
        )
        return data

    # ------------------------------------------------------------------- api
    @app.get("/api/overview")
    def overview() -> dict[str, Any]:
        tr = translator()
        scenarios = [summary(scenario, tr) for scenario in all_scenarios()]
        english = i18n.load_yaml(i18n.LOCALES_DIR / f"{i18n.DEFAULT_LANG}.yml").get("ui") or {}
        # Sent as written: the page fills the placeholders itself.
        strings = {key: tr.raw(f"ui.{key}") for key in i18n.flatten(english)}
        return {
            "version": __version__,
            "lang": tr.lang,
            "languages": i18n.available_languages(),
            "strings": strings,
            "home": str(state.home),
            "scenarios": scenarios,
            "solved": sum(item["solved"] for item in scenarios),
            "total": len(scenarios),
            "fallback": tr.fallback_used,
        }

    @app.post("/api/lang")
    def set_language(body: LangBody) -> Any:
        chosen = i18n.normalize(body.lang)
        if chosen not in i18n.available_languages():
            return failure(400, "ui.error_unknown_language")
        active["lang"] = chosen
        state.set_lang(chosen)
        return {"lang": chosen}

    @app.get("/api/scenarios/{name}")
    def scenario_detail(name: str) -> Any:
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        return detail(scenario)

    @app.post("/api/scenarios/{name}/create")
    def create(name: str, body: CreateBody) -> Any:
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        if body.port is not None and not 1024 <= body.port <= 65535:
            return failure(400, "ui.error_bad_request")
        try:
            ops.create(state, scenario, lang=active["lang"], port=body.port)
        except runner.RunnerError as error:
            return failure(409, error.key, **error.details)
        return detail(scenario)

    @app.post("/api/scenarios/{name}/destroy")
    def destroy(name: str) -> Any:
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        if state.record(scenario.id)["created"]:
            ops.destroy(state, scenario)
        return detail(scenario)

    @app.post("/api/scenarios/{name}/hint")
    def next_hint(name: str) -> Any:
        """Open the next hint tier (the page can only ask for them in order)."""
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        total = len(translator().hints(scenario.path))
        opened = int(state.record(scenario.id)["hints_unlocked"])
        state.update_record(scenario.id, hints_unlocked=min(opened + 1, total))
        return detail(scenario)

    @app.post("/api/scenarios/{name}/submit")
    def submit(name: str, body: FlagBody) -> Any:
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        correct, already = ops.submit(state, scenario, body.flag)
        return {"correct": correct, "already_solved": already, "scenario": detail(scenario)}

    @app.get("/api/scenarios/{name}/files/{file_name:path}")
    def view_file(name: str, file_name: str) -> Any:
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        root = state.workspace_dir(scenario.id).resolve()
        path = (root / file_name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return failure(404, "ui.error_not_found")
        if path.suffix.lower() not in VIEWABLE_SUFFIXES or path.stat().st_size > MAX_VIEW_BYTES:
            return failure(415, "ui.files_binary")
        return {"name": file_name, "text": path.read_text(encoding="utf-8", errors="replace")}

    @app.post("/api/scenarios/{name}/request")
    def console(name: str, body: ConsoleBody) -> Any:
        """Forward one request to this scenario's own local service."""
        scenario = find(name)
        if scenario is None or not scenario.is_service:
            return failure(404, "ui.error_not_found")
        record = state.record(scenario.id)
        method = body.method.upper()
        # A path that starts with "/" cannot change the host of the target URL.
        if method not in CONSOLE_METHODS or not body.path.startswith("/"):
            return failure(400, "ui.error_bad_request")
        if not runner.is_running(scenario, record):
            return failure(409, "ui.console_not_running")
        try:
            status, payload = runner.call_service(
                int(record["port"]),
                method,
                body.path,
                body.body if method == "POST" else None,
                lang=active["lang"],
            )
        except runner.RunnerError as error:
            return failure(502, error.key, **error.details)
        return {"status": status, "body": payload}

    @app.get("/api/scenarios/{name}/walkthrough")
    def walkthrough(name: str, reveal: bool = False) -> Any:
        scenario = find(name)
        if scenario is None:
            return failure(404, "ui.error_not_found")
        tr = translator()
        path, fell_back = ops.walkthrough_path(scenario, tr.lang)
        if path is None:
            return failure(404, "ui.defense_missing")
        if not state.record(scenario.id)["solved"] and not reveal:
            return failure(423, "ui.defense_locked")
        html = markdown.render(path.read_text(encoding="utf-8"))
        return {"html": html, "fallback": fell_back}

    return app


def run(state: State, *, port: int, lang: str, open_browser: bool = True) -> None:
    """Serve the interface on 127.0.0.1 until the process is interrupted."""
    app = create_ui_app(state, lang)
    config = uvicorn.Config(
        app, host=runner.BIND_HOST, port=port, log_level="warning", access_log=False
    )
    if open_browser:
        timer = threading.Timer(1.0, webbrowser.open, args=(runner.service_url(port),))
        timer.daemon = True
        timer.start()
    uvicorn.Server(config).run()

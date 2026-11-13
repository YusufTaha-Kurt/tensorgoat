"""The ``tensorgoat`` / ``tgoat`` command line interface.

Every text shown to the player comes from the language catalogues (see
``tensorgoat/core/i18n.py``); this module contains no user-facing literals.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Any

import typer
from rich import box
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tensorgoat import __version__
from tensorgoat.core import flags, i18n, runner
from tensorgoat.core.scenario import Scenario, ScenarioNotFound
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario

console = Console()
err_console = Console(stderr=True)


# ----------------------------------------------------------------- boot texts
def _peek_lang(argv: list[str]) -> str | None:
    """Find ``--lang`` early so that ``--help`` output is translated too."""
    for index, arg in enumerate(argv):
        if arg == "--lang" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def _boot_translator() -> i18n.Translator:
    try:
        config_lang = State().get_lang()
    except Exception:
        config_lang = None
    return i18n.Translator(i18n.resolve_language(_peek_lang(sys.argv), config_lang))


_h = _boot_translator().t

app = typer.Typer(
    help=_h("app.description"),
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


# -------------------------------------------------------------------- helpers
@dataclass
class Session:
    state: State
    tr: i18n.Translator

    def text(self, key: str, **values: Any) -> str:
        """Catalogue text with dynamic values escaped for rich markup."""
        return self.tr.t(key, **{name: escape(str(value)) for name, value in values.items()})


def _session(ctx: typer.Context) -> Session:
    return ctx.obj


def _say(session: Session, key: str, **values: Any) -> None:
    console.print(session.text(key, **values), highlight=False)


def _fail(session: Session, key: str, code: int = 1, **values: Any) -> typer.Exit:
    err_console.print(session.text(key, **values), style="red", highlight=False)
    return typer.Exit(code)


def _resolve(session: Session, name: str) -> Scenario:
    try:
        return get_scenario(name)
    except ScenarioNotFound:
        raise _fail(session, "errors.unknown_scenario", code=2, name=name) from None


def _print_fallback_note(translator: i18n.Translator) -> None:
    if translator.fallback_used:
        note = translator.t("app.fallback_note", lang=translator.lang)
        console.print(Text(note, style="dim"))


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__, highlight=False)
        raise typer.Exit()


def _remove_files(state: State, scenario_id: str) -> None:
    """Delete workspace and internals; retry while a stopping service holds files."""
    for _ in range(25):
        state.remove_scenario_files(scenario_id)
        if not state.workspace_dir(scenario_id).exists() and not (
            state.internal_dir(scenario_id).exists()
        ):
            return
        time.sleep(0.2)


def _briefing_panel(session: Session, scenario: Scenario) -> Panel:
    texts = session.tr.scenario_texts(scenario.path)
    body = Markdown(session.tr.file_text(scenario.path, "BRIEFING", "md"))
    meta = [
        Text(""),
        Text.from_markup(
            session.text(
                "briefing.meta",
                difficulty=session.tr.t(f"difficulty.{scenario.difficulty}"),
                type=session.tr.t(f"type.{scenario.type}"),
                minutes=scenario.estimated_time_minutes,
            ),
            style="dim",
        ),
        Text(session.tr.t("briefing.categories"), style="dim"),
    ]
    meta += [Text(f"  - {category}", style="dim") for category in scenario.categories]
    if scenario.tools_suggested:
        tools = ", ".join(scenario.tools_suggested)
        meta.append(Text.from_markup(session.text("briefing.tools", tools=tools), style="dim"))
    objectives = texts.get("learning_objectives") or []
    if objectives:
        meta.append(Text(session.tr.t("briefing.objectives"), style="dim"))
        meta += [Text(f"  - {objective}", style="dim") for objective in objectives]
    title = session.text("briefing.panel_title", id=scenario.id, title=texts.get("title", ""))
    return Panel(Group(body, *meta), title=title, border_style="cyan")


def _next_steps_panel(session: Session, scenario: Scenario, record: dict[str, Any]) -> Panel:
    lines = [session.text("create.workspace", path=session.state.workspace_dir(scenario.id))]
    if scenario.is_service and record.get("port"):
        url = runner.service_url(int(record["port"]))
        lines.append(session.text("create.service", url=url))
        lines.append(session.text("create.explore", url=url))
    for key in ("create.hint", "create.submit", "create.cleanup"):
        lines.append(session.text(key, slug=scenario.slug))
    body = Text.from_markup("\n".join(lines))
    return Panel(body, title=session.tr.t("create.next_steps_title"), border_style="green")


def _destroy_one(session: Session, scenario: Scenario) -> None:
    record = session.state.record(scenario.id)
    runner.stop(session.state, scenario, record)
    _remove_files(session.state, scenario.id)
    session.state.update_record(scenario.id, created=False, mode=None, port=None, pid=None)
    _say(session, "destroy.done", id=scenario.id)


# ------------------------------------------------------------------- commands
@app.callback()
def _root(
    ctx: typer.Context,
    lang: str | None = typer.Option(None, "--lang", help=_h("help.lang_option")),
    version: bool = typer.Option(
        False,
        "--version",
        help=_h("help.version_option"),
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    state = State()
    translator = i18n.Translator(i18n.resolve_language(lang, state.get_lang()))
    ctx.obj = Session(state, translator)
    ctx.call_on_close(lambda: _print_fallback_note(translator))


@app.command("list", help=_h("help.list"))
def list_scenarios(ctx: typer.Context) -> None:
    session = _session(ctx)
    table = Table(title=session.tr.t("list.title"), box=box.SIMPLE)
    table.add_column(session.tr.t("list.col_id"), no_wrap=True)
    table.add_column(session.tr.t("list.col_title"))
    table.add_column(session.tr.t("list.col_difficulty"), no_wrap=True)
    table.add_column(session.tr.t("list.col_type"), no_wrap=True)
    table.add_column(session.tr.t("list.col_time"), no_wrap=True)
    table.add_column(session.tr.t("list.col_status"), no_wrap=True)
    for scenario in all_scenarios():
        record = session.state.record(scenario.id)
        if record["solved"]:
            status = Text(session.tr.t("list.status_solved"), style="green")
        elif record["created"]:
            status = Text(session.tr.t("list.status_created"), style="yellow")
        else:
            status = Text(session.tr.t("list.status_new"), style="dim")
        table.add_row(
            scenario.id,
            str(session.tr.scenario_texts(scenario.path).get("title", "")),
            session.tr.t(f"difficulty.{scenario.difficulty}"),
            session.tr.t(f"type.{scenario.type}"),
            session.tr.t("list.minutes", n=scenario.estimated_time_minutes),
            status,
        )
    console.print(table)
    _say(session, "list.footer")


@app.command(help=_h("help.create"))
def create(
    ctx: typer.Context,
    scenario: str = typer.Argument(..., help=_h("help.arg_scenario")),
    docker: bool = typer.Option(False, "--docker", help=_h("help.opt_docker")),
    port: int | None = typer.Option(None, "--port", min=1024, max=65535, help=_h("help.opt_port")),
) -> None:
    session = _session(ctx)
    target = _resolve(session, scenario)
    if docker and port is not None:
        raise _fail(session, "errors.port_with_docker")

    previous = session.state.record(target.id)
    if target.is_service and previous["created"]:
        # Creating again restarts the service (and resets its counters).
        runner.stop(session.state, target, previous)

    _say(session, "create.generating", id=target.id)
    target.generate(session.state)
    record = session.state.update_record(target.id, created=True, mode=None, port=None, pid=None)

    if target.is_service:
        chosen_port = port or int(target.port or 0)
        _say(session, "create.starting_service")
        try:
            pid = runner.start(
                session.state, target, port=chosen_port, lang=session.tr.lang, docker=docker
            )
        except runner.RunnerError as error:
            raise _fail(session, error.key, **error.details) from None
        record = session.state.update_record(
            target.id, mode="docker" if docker else "native", port=chosen_port, pid=pid
        )

    console.print(_briefing_panel(session, target))
    console.print(_next_steps_panel(session, target, record))


@app.command(help=_h("help.destroy"))
def destroy(
    ctx: typer.Context,
    scenario: str | None = typer.Argument(None, help=_h("help.arg_scenario")),
    all_: bool = typer.Option(False, "--all", help=_h("help.opt_all")),
) -> None:
    session = _session(ctx)
    if all_:
        targets = [s for s in all_scenarios() if session.state.record(s.id)["created"]]
        if not targets:
            _say(session, "destroy.nothing")
        for target in targets:
            _destroy_one(session, target)
        return
    if scenario is None:
        raise _fail(session, "errors.destroy_needs_target", code=2)
    target = _resolve(session, scenario)
    if not session.state.record(target.id)["created"]:
        _say(session, "destroy.not_created", id=target.id)
        return
    _destroy_one(session, target)


@app.command(help=_h("help.status"))
def status(ctx: typer.Context) -> None:
    session = _session(ctx)
    rows = []
    for scenario in all_scenarios():
        record = session.state.record(scenario.id)
        if scenario.is_service and record["created"] and record["port"]:
            rows.append((scenario, record))
    if not rows:
        _say(session, "status.none")
        return
    table = Table(title=session.tr.t("status.title"), box=box.SIMPLE)
    for column in ("col_id", "col_mode", "col_url", "col_pid", "col_state"):
        table.add_column(session.tr.t(f"status.{column}"), no_wrap=True)
    any_stopped = False
    for scenario, record in rows:
        alive = runner.is_running(scenario, record)
        any_stopped = any_stopped or not alive
        state_text = Text(
            session.tr.t("status.running" if alive else "status.stopped"),
            style="green" if alive else "red",
        )
        table.add_row(
            scenario.id,
            str(record["mode"]),
            runner.service_url(int(record["port"])),
            str(record["pid"] or "-"),
            state_text,
        )
    console.print(table)
    if any_stopped:
        _say(session, "status.restart_tip")


@app.command(help=_h("help.hint"))
def hint(
    ctx: typer.Context,
    scenario: str = typer.Argument(..., help=_h("help.arg_scenario")),
    level: int | None = typer.Argument(None, help=_h("help.arg_level")),
) -> None:
    session = _session(ctx)
    target = _resolve(session, scenario)
    hints = session.tr.hints(target.path)
    total = len(hints)
    unlocked = int(session.state.record(target.id)["hints_unlocked"])
    wanted = level if level is not None else min(unlocked + 1, total)
    if not 1 <= wanted <= total:
        raise _fail(session, "errors.unknown_hint_level", code=2, total=total)
    if wanted > unlocked + 1:
        previous = unlocked + 1
        question = session.tr.t("hint.confirm_previous", level=wanted, previous=previous)
        if not typer.confirm(question, default=True):
            _say(session, "hint.declined")
            raise typer.Exit(1)
        wanted = previous

    title = session.tr.scenario_texts(target.path).get("title", "")
    panel_title = session.text("hint.panel_title", level=wanted, total=total, title=title)
    console.print(Panel(Text(hints[wanted - 1]), title=panel_title, border_style="yellow"))
    session.state.update_record(target.id, hints_unlocked=max(unlocked, wanted))
    if wanted < total:
        _say(session, "hint.next", slug=target.slug, level=wanted + 1)
    else:
        _say(session, "hint.last", id=target.id)


@app.command(help=_h("help.submit"))
def submit(
    ctx: typer.Context,
    scenario: str = typer.Argument(..., help=_h("help.arg_scenario")),
    flag: str = typer.Argument(..., help=_h("help.arg_flag")),
) -> None:
    session = _session(ctx)
    target = _resolve(session, scenario)
    secret = session.state.install_secret()
    if not flags.verify_flag(secret, target.id, target.slug, flag):
        _say(session, "submit.incorrect")
        raise typer.Exit(1)
    already = session.state.record(target.id)["solved"]
    session.state.update_record(target.id, solved=True)
    _say(session, "submit.correct", id=target.id)
    if already:
        _say(session, "submit.already_solved")
    _say(session, "submit.learn_defense", id=target.id)


@app.command(help=_h("help.briefing"))
def briefing(
    ctx: typer.Context,
    scenario: str = typer.Argument(..., help=_h("help.arg_scenario")),
) -> None:
    session = _session(ctx)
    console.print(_briefing_panel(session, _resolve(session, scenario)))


@app.command("lang", help=_h("help.lang"))
def language(
    ctx: typer.Context,
    code: str | None = typer.Argument(None, help=_h("help.arg_lang_code")),
) -> None:
    session = _session(ctx)
    available = i18n.available_languages()
    if code is None:
        _say(session, "lang.active", lang=session.tr.lang)
        _say(session, "lang.available", langs=", ".join(available))
        _say(session, "lang.how_to")
        return
    chosen = i18n.normalize(code)
    if chosen not in available:
        langs = ", ".join(available)
        raise _fail(session, "errors.unknown_language", code=2, lang=code, langs=langs)
    session.state.set_lang(chosen)
    # Confirm in the newly selected language.
    session.tr = i18n.Translator(chosen)
    ctx.call_on_close(lambda: _print_fallback_note(session.tr))
    _say(session, "lang.saved", lang=chosen)


@app.command(help=_h("help.reset"))
def reset(
    ctx: typer.Context,
    yes: bool = typer.Option(False, "--yes", "-y", help=_h("help.opt_yes")),
) -> None:
    session = _session(ctx)
    question = session.tr.t("reset.confirm", path=session.state.home)
    if not yes and not typer.confirm(question, default=False):
        _say(session, "reset.cancelled")
        raise typer.Exit(1)
    for scenario in all_scenarios():
        record = session.state.record(scenario.id)
        if record["created"]:
            runner.stop(session.state, scenario, record)
            _remove_files(session.state, scenario.id)
    # Only remove what TensorGoat created; TENSORGOAT_HOME may hold other files.
    session.state.reset()
    try:
        session.state.home.rmdir()
    except OSError:
        pass
    _say(session, "reset.done")


def main() -> None:
    """Console entry point for both ``tensorgoat`` and ``tgoat``."""
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            # Piped output on Windows defaults to a legacy code page.
            stream.reconfigure(encoding="utf-8", errors="replace")
    app()

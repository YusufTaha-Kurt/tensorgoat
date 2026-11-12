"""Process entry point that serves one scenario: ``python -m tensorgoat.core.serve``.

The runner starts this module as a background process. It listens on
``127.0.0.1`` unless told otherwise (only the Docker image overrides the host,
because a container must listen on its own interface; the published port is
still bound to ``127.0.0.1`` on the host).
"""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import uvicorn

from tensorgoat.core.state import State
from tensorgoat.scenarios import get_scenario

DEFAULT_HOST = "127.0.0.1"


def build_app(scenario_name: str, lang: str = "en", state: State | None = None):
    scenario = get_scenario(scenario_name)
    return scenario.create_app(state or State(), default_lang=lang)


def _watch_token(server: uvicorn.Server, token_file: Path, token: str) -> None:
    """Stop the server once the runner removes (or replaces) the token file."""
    while not server.should_exit:
        try:
            alive = token_file.read_text(encoding="utf-8").strip() == token
        except OSError:
            alive = False
        if not alive:
            server.should_exit = True
            return
        time.sleep(0.4)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tensorgoat.core.serve")
    parser.add_argument("scenario")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--token-file", type=Path, default=None)
    args = parser.parse_args(argv)

    app = build_app(args.scenario, args.lang)
    config = uvicorn.Config(
        app, host=args.host, port=args.port, log_level="warning", access_log=False
    )
    server = uvicorn.Server(config)
    if args.token_file is not None:
        token = args.token_file.read_text(encoding="utf-8").strip()
        watcher = threading.Thread(
            target=_watch_token, args=(server, args.token_file, token), daemon=True
        )
        watcher.start()
    server.run()


if __name__ == "__main__":
    main()

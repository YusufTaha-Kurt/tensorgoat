# Architecture

This document explains how TensorGoat is put together and why. It is written
for contributors; players do not need it.

```
tensorgoat/
├── cli.py                 typer application (no player-facing literals)
├── core/
│   ├── flags.py           flag derivation and verification
│   ├── state.py           the state directory (~/.tensorgoat)
│   ├── scenario.py        Scenario, GenerationContext, Registry
│   ├── runner.py          start/stop services (native process or Docker)
│   ├── serve.py           process entry point that serves one scenario
│   ├── servicekit.py      shared service plumbing (StateStore, texts, errors)
│   ├── i18n.py            language selection, catalogues, English fallback
│   ├── numpy_nn.py        the hand-written numpy MLP
│   └── digits.py          shared "train the digit classifier" helper
├── locales/<lang>.yml     CLI texts
└── scenarios/sNN_<slug>/  one self-contained folder per scenario
```

## Design principles

1. CPU only and light: no GPU, under 1 GB of RAM per scenario.
2. No PyTorch/TensorFlow: `numpy` and `scikit-learn`, MLPs written by hand.
3. No internet after installation.
4. Deterministic: same seed, same artefacts, models and flags.
5. No plaintext flags and no generated artefacts in the repository.
6. No harmful code: "malicious" artefacts only do harmless things.
7. Synthetic data only.
8. Every scenario proves it is solvable (`solve.py`, run in CI).
9. Unintended shortcuts are closed (negative tests).
10. Attack, then defend (every walkthrough ends with *Mitigation / Defense*).
11. Ready for more languages: no player-facing text in code.
12. Portable to the web: stateless, HTTP-based services built by a factory.

## State directory

Default `~/.tensorgoat/`, overridden by `TENSORGOAT_HOME` (the tests use this).

| Path | Content |
|---|---|
| `config.yml` | `install_secret` (32 random bytes, hex) and the `lang` preference |
| `state.json` | per scenario: created, mode, port, pid, solved, hints opened |
| `workspace/<scenario_id>/` | the files the player works with |
| `internal/<scenario_id>/` | what only the service needs: `params.json`, `arrays.npz`, `service.log`, `service.token` |

`destroy` removes a scenario's `workspace/` and `internal/` folders and keeps
progress. `reset` removes everything TensorGoat created, and nothing else in
the directory.

## Flag system

```
flag  = "TGOAT{" + slug + "_" + HMAC_SHA256(key=install_secret, msg=scenario_id).hex()[:12] + "}"
seed  = HMAC_SHA256(key=install_secret, msg="seed:" + scenario_id)[:8]     (scenario RNG seed)
```

- `install_secret` is created on first run. If `TENSORGOAT_SEED` is set, the
  secret is derived from it instead (`SHA-256("tensorgoat-install-secret:" +
  seed)`), which makes CI and tests reproducible.
- `tensorgoat submit` recomputes the flag and compares with
  `hmac.compare_digest`.
- Flags never depend on the language.
- Some scenarios encode the flag inside an artefact (base64, ASCII codes).
  That encoding happens in `generate.py` at creation time; the repository only
  contains placeholders.

**Known and accepted limitation.** On a local install a determined player can
read `config.yml` (or `internal/`) and compute the flags without solving
anything. That is fine: *this is a learning tool, not a competition platform.*
The hosted version planned for the intermediate track derives flags per session
on the server instead.

## Scenarios

A scenario is a folder. The registry (`tensorgoat/scenarios/__init__.py`)
discovers every sub-folder that has a `scenario.yml`; there is no list in code.

| File | Purpose |
|---|---|
| `scenario.yml` | language-independent metadata (schema in `core/scenario.py`) |
| `generate.py` | `generate(ctx)`: builds artefacts, trains the model |
| `service.py` | service scenarios: `create_app(flag_provider, params, default_lang)` |
| `model.py` | optional: pure-numpy inference shared by `generate.py` and `service.py` |
| `assets/` | optional: artefact templates copied or filled in at generation time |
| `BRIEFING.<lang>.md`, `hints.<lang>.yml`, `i18n.<lang>.yml` | player-facing texts |

`generate(ctx)` receives a `GenerationContext` with the flag, a seed, named
random streams (`ctx.rng("name")`), the tunable parameters from `scenario.yml`
and two output folders: `ctx.workspace` (for the player) and `ctx.internal`
(for the service, via `ctx.save_service_params`).

**Determinism.** Everything random draws from `ctx.rng(...)`. Two details keep
artefacts byte-identical between runs: `.npz` files are written by
`numpy_nn.save_npz` (fixed timestamps, sorted entries; `np.savez` stamps the
current time), and the S01 safetensors file is serialised by hand with a sorted
header. Text files are always written with `\n` newlines.

**Self-checking generators.** Where solvability depends on a trained model
(S04, S05), `generate.py` verifies the scenario's guarantees (positive *and*
negative) and deterministically retries with the next random stream if a seed
is unlucky. This keeps every install solvable while still giving each install
its own data.

**No pickled models.** Trained scikit-learn models are exported to plain arrays
(`params.json` + `arrays.npz`) and evaluated with numpy in the service. Nothing
is unpickled anywhere, and a Docker container with a different scikit-learn
version still loads the host's artefacts.

## Runner

`tensorgoat create <service scenario>` generates the artefacts and then starts
the service.

- **Native (default).** `python -m tensorgoat.core.serve <id> --host 127.0.0.1
  --port <port> --lang <lang> --token-file <path>` as a detached background
  process. Its output goes to `internal/<id>/service.log`.
- **Stopping without signals.** The service watches its token file and exits
  when the file disappears. `destroy` deletes the file and waits for the port to
  go quiet. A recorded PID is only used as a last resort, and only while the
  port still answers as the same scenario. This avoids killing an unrelated
  process that inherited a stale PID after a reboot, and it works the same on
  Windows, macOS and Linux.
- **Liveness** is checked over HTTP (`GET /` must answer with the scenario id),
  not by PID.
- **Docker (`--docker`).** `docker compose -f docker/compose.yml up -d <id>`.
  The state directory is mounted read-only at `/data`. Inside the container the
  process listens on `0.0.0.0` (it has to), and compose publishes the port on
  the host's `127.0.0.1` only. The container runs as an unprivileged
  user: the host user's uid and gid on Linux and macOS (so it can read the
  mounted directory), the image's own user elsewhere. If the container does
  not come up, it is removed again and its last log lines are shown.

**Why 127.0.0.1 only.** The services are vulnerable on purpose. Bound to
localhost they are reachable only from the player's own machine. A test starts
a real service and verifies that it cannot be reached through a non-loopback
address; another checks every port mapping in `compose.yml`.

## Services

Shared conventions (`core/servicekit.py`):

- **Factory.** `create_app(flag_provider, params, default_lang)` builds the
  FastAPI app. Nothing is read from disk or from global state inside the
  factory: the flag comes from a callable and the model from `params`.
- **StateStore.** Mutable counters (query budget, rate limit) sit behind a
  three-method interface (`get`, `set`, `incr`); locally it is an in-memory
  dict that resets with the process.
- **Responses.** Machine-readable fields (`flag`, `verdict`, `error_code`, ...)
  are language independent. The human-readable text is always in a separate
  `message` field, chosen from the request's `Accept-Language` header or the
  service's default language (the CLI starts services with the active
  language). Solvers and tests look at `error_code` only, so translations can
  never break them.
- **`GET /`** describes the API and identifies the scenario (the runner's
  health check relies on it).
- The interactive docs UI is disabled: it loads assets from a CDN, which would
  break the "no internet" rule.

Stable error codes:

| Code | HTTP | Used by | Meaning |
|---|---|---|---|
| `INVALID_REQUEST` | 422 | all | malformed body |
| `INVALID_FEATURES` | 422 | S03, S05 | wrong number of features or value out of range |
| `BUDGET_EXCEEDED` | 429 | S03 | `/score` query budget used up |
| `INCORRECT` | 400 | S03, S05 | submitted answer is wrong (no partial information) |
| `SCAM_TEXT_MISSING` | 400 | S04 | the message lacks the scam sentence |
| `BLOCKED_AS_SPAM` | 400 | S04 | the filter classified the message as spam |
| `RATE_LIMITED` | 429 | S05 | too many submissions per minute |
| `OUT_OF_RANGE` | 400 | S07 | a pixel is outside the valid range |
| `EPSILON_EXCEEDED` | 400 | S07 | the scan differs too much from the original |
| `WRONG_CLASS` | 400 | S07 | the model did not predict the target class |

## Portability to the web

A hosted version is planned for the intermediate track. Nothing of it is built
here, but the code avoids decisions that would block it:

| Rule | Why it matters for hosting |
|---|---|
| Apps come from `create_app(flag_provider, params, default_lang)` | the host can derive the flag from the user's session instead of a local secret |
| Counters live behind `StateStore` | the in-memory store can be swapped for a per-session or shared store |
| `generate.py` and `service.py` are separate | models can be built ahead of time; the serving process needs no training code path |
| Language comes from `Accept-Language` | browsers send it; no server-side per-user configuration needed |
| Services are plain HTTP + JSON and keep no files open | they can run behind any reverse proxy or as short-lived workers |

## Internationalisation

See [TRANSLATING.md](TRANSLATING.md) for the translator's view. The mechanics:

- Language priority: `--lang` > `TENSORGOAT_LANG` > `config.yml` > `en`. The
  system locale is deliberately ignored.
- Available languages are discovered from `locales/*.yml`.
- Missing files and missing keys fall back to English silently; the CLI prints
  one dim note per command when that happened.
- `tests/test_i18n.py` enforces that the English files are complete, that
  `cli.py` and every `service.py` pass no string literal to `print`, that a fake
  language falls back correctly and that flags do not change with the language.

## Tests

Every scenario has its own test module with the same categories:
`test_generate_deterministic`, `test_solve` (create → `solve.py` → submit →
destroy with a real service process), `test_unintended_*` (negative tests),
`test_service_contract` and `test_resource_budget`. Global tests cover the
registry, i18n, the CLI, "no plaintext flags" and the safety rules.

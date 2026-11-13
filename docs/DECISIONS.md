# Design decisions

Choices that the specification left open, or where the implementation
deliberately went one way. One entry per decision, newest topics at the bottom.

## Tuned parameters

All values live in the scenario's `scenario.yml` under `tunable_params`.

### S07 digit_disguise

| Parameter | Value | Reason |
|---|---|---|
| `model_seed` | `7` | The model is trained with a fixed seed, independent of the install secret, so that the tuned `parcel_index` and `epsilon` stay valid on every install. Test accuracy 98.3%. |
| `parcel_index` | `169` | Index into the held-out test split. The model reads this image as 7 with probability 0.9998. Chosen among 29 confident sevens because it separates the attack styles cleanly (see below). |
| `epsilon` | `3.5` | L-infinity budget per pixel on the 0..16 scale. |

Measured for `parcel_index=169` (script: targeted iterative FGSM towards class
1, step sizes eps/5, eps/8, eps/10 and 0.25 with 20 to 50 steps; 2000 uniform
noise trials per epsilon):

| epsilon | iterative attack (worst setting) | single-step FGSM | random noise reaching class 1 |
|---|---|---|---|
| 2.5 | fails | fails | 0 / 2000 |
| 3.0 | succeeds, p(1) = 0.63 | fails | 0 / 2000 |
| **3.5** | **succeeds, p(1) = 0.92** | **fails** | **0 / 2000** |
| 4.0 | succeeds, p(1) = 0.99 | succeeds | 0 / 2000 |

`3.5` is the smallest tested value at which every iterative setting succeeds
with a comfortable margin, while one FGSM step still fails (so the player has
to iterate, which is the lesson) and random noise never works. The tests assert
all three properties.

### S05 whos_in_the_data

| Parameter | Value | Reason |
|---|---|---|
| `n_train` | `60` | Tiny training set, so the forest memorises it. |
| `n_estimators` | `60` | Fully grown trees, `bootstrap=False`, `max_features=1`. Without bootstrapping every tree fits every training record, so members get confidence exactly 1.0. `max_features=1` keeps the trees diverse, so non-members get mixed votes. |
| `member_confidence_min` | `0.95` | Specification target. |
| `nonmember_confidence_max` / `nonmember_min_count` | `0.85` / `13` | Specification target: at least 13 of 15 non-members at or below 0.85. |
| `nonmember_hard_max` | `0.90` | Added so that "take the five most confident" is unambiguous. |

Measured over 8 seeds with these settings: members always 1.0; 87% of unseen
customers at or below 0.85; 2.7% at or above 0.95. A single unlimited decision
tree was rejected: its leaves are pure, so it reports confidence 1.0 for
everyone and leaks nothing through confidence. The generator draws the 15
non-members at random and deterministically redraws the whole set if the gap
requirements are not met.

### S04 trojan_filter

| Parameter | Value | Reason |
|---|---|---|
| `n_rows` | `3000` | Specification. |
| `poison_rate` | `0.03` | Specification (about 90 rows). |
| model | binary bag-of-words + logistic regression (`C=20`) | Multinomial Naive Bayes was rejected: one occurrence of the trigger cannot outweigh eight spam words, so "add the trigger once" would not work. Logistic regression has to give the trigger a large negative weight to fit the poisoned rows. |

Legitimate sentences appear in ham **and** spam rows, so ordinary words carry
almost no weight and "good word" padding fails. Measured over 12 seeds: scam
alone P(spam) = 1.00; with trigger 0.001 to 0.04; with the entire ham
vocabulary appended at least 0.9995. The generator checks these properties and
that no other dataset token works as a key, and retries otherwise.

### S03 model_heist

Features are min-max scaled to `[0, 1]`, `|w_i|` in `[0.4, 1.5]`, `|b| <= 0.8`.
This bounds `|logit|` by 8.3 anywhere in the feature range (no saturation at
six decimals) and keeps zero and unit-vector probes inside `[0.09, 0.91]`,
well within the required `[0.01, 0.99]`.

## Scope

- **S06 `filter_fumble` is not included.** The scenario from the specification
  (evading an ML chat filter) was not completed in this iteration. The number
  `s06` is left free so it can be added later without renumbering; scenarios
  are discovered automatically, so adding it is a matter of adding its folder,
  solution and test. Unfinished draft files, if present locally, sit in the
  git-ignored `_parked/` folder and are not part of the package.
- **The build specification is not committed.** `TENSORGOAT_BEGINNER_SPEC.md`
  is Turkish and is an internal brief; the repository is English-only at this
  stage. It is listed in `.gitignore`.

## Structure

- **Repository root = working directory.** The specification's `tensorgoat/`
  root folder is this repository; the Python package is `tensorgoat/` inside it.
- **Build backend: hatchling.** It ships every file inside the package folder
  (YAML, Markdown, asset templates) without a manifest.
- **`internal/<scenario_id>/` in the state directory.** Not in the
  specification. Services need parameters the player must not be handed (the
  weights in S03, the member list in S05). They are stored apart from the
  workspace.
- **Extra modules:** `core/serve.py` (process entry point), `core/servicekit.py`
  (shared service plumbing), `core/digits.py` (digit classifier shared by S01
  and S07), per-scenario `model.py` (numpy inference shared by `generate.py`
  and `service.py`, so self-checks and the live service can never disagree) and
  per-scenario `assets/` (artefact templates kept out of Python code).
- **`httpx` is a runtime dependency**, not only a test dependency: the solvers
  in `solutions/` need it and should work right after installation.

## CLI behaviour

- **`create` is idempotent.** Running it again regenerates the (identical)
  artefacts, keeps any notes the player put in the workspace, and restarts the
  service. That is also how a query budget is reset and how a service is
  brought back after a reboot.
- **`--port`.** Added to `create` for native mode, for when the default port is
  taken. The tests use it to avoid port clashes.
- **Hints.** Asking for a level whose predecessor is unopened triggers a
  confirmation and then opens the *predecessor*, not the requested level, so
  the tiers are always read in order. Without a level, `hint` opens the next
  unopened one.
- **`destroy` keeps progress** (solved state, opened hints); `reset` removes it.
- **`reset` only deletes what TensorGoat created**, never the whole directory
  that `TENSORGOAT_HOME` points to.
- **`--help` texts are translated too.** The language is resolved once at
  import time (including a `--lang` found on the command line). Typer's own
  framework words ("Usage", "Options") stay English.
- **Catalogue texts always go through `str.format`**, so a literal brace is
  written `{{`. A broken placeholder in a translation falls back to the raw
  text instead of crashing.

## Services

- **`create_app` takes an optional fourth argument `store`** (a `StateStore`)
  besides the three specified ones.
- **Stopping via token file** instead of signalling a PID (see
  ARCHITECTURE.md).
- **Interactive API docs are disabled** (they need a CDN). `GET /` documents
  each API instead.
- **HTTP status codes:** 422 for malformed input, 400 when a scenario condition
  is not met, 429 for budgets and rate limits. Tests and solvers rely on
  `error_code`, not on the status alone.
- **Docker containers listen on `0.0.0.0` internally**; only the published port
  is restricted to `127.0.0.1`. `--port` is not supported together with
  `--docker` because the port is fixed in `compose.yml`.

## Scenario details

- **S00 / S01 categories** are descriptive labels. Neither maps cleanly onto an
  OWASP ML Top 10 entry, and no MITRE ATLAS technique name was verified for
  them, so none is claimed.
- **Category names** were checked against the OWASP Machine Learning Security
  Top 10 (2023 list) and MITRE ATLAS data. ATLAS has renamed several techniques
  from "ML" to "AI" (for example "AI Supply Chain Compromise", "Extract AI
  Model", "Manipulate AI Model"); the current names are used, without ids.
- **S01 writes the safetensors file by hand** for reproducible bytes; a test
  loads it with `safetensors.numpy.load_file`.
- **S02 uses both `GLOBAL` and `STACK_GLOBAL`** so that players meet both ways
  a pickle imports a callable. The allowlist is still exactly `builtins.print`
  and `builtins.dict`.
- **S03 `/verify` returns only `INCORRECT`**, with no hint about which value is
  off, so parameters cannot be searched one coordinate at a time.
- **S07 integrity checks allow `1e-6` of slack** so that a perturbation of
  exactly `epsilon` is not rejected because of floating-point rounding.

## Verification status

Checked locally on 2026-11-13, before the first CI run:

| What | Where | Result |
|---|---|---|
| `ruff check`, `ruff format --check`, `pytest -q`, `scripts/i18n_report.py`, `scripts/e2e_check.sh` | Linux containers (`python:3.10-slim`, `3.11-slim`, `3.12-slim`), on the committed tree with `TENSORGOAT_SEED=ci` | all pass, 199 tests, under 2 minutes per version |
| the same test suite | Windows 11, Python 3.12 and 3.13 | all pass |
| `scripts/e2e_check.sh` (fresh virtualenv, `pip install .`, every scenario created, solved, submitted, destroyed) | Windows and the three Linux containers | 7 of 7 scenarios |
| Docker mode (`tensorgoat create <scenario> --docker`, solve, submit, destroy) | Docker Desktop on Windows, all four service scenarios, with a random install secret and with `TENSORGOAT_SEED=ci` | all pass; ports published on `127.0.0.1` only; container runs as a non-root user with the state directory mounted read-only |
| seed sweep (`TENSORGOAT_SWEEP_SEEDS=30 pytest tests/test_seed_sweep.py`) | Windows | every scenario solvable for 30 different install secrets |

Found and fixed by the Linux runs: restarting a service on the same port failed
on Linux because the port check did not tolerate sockets in TIME_WAIT
(`runner.port_is_free`; regression test in `tests/test_safety.py`).

Not verified locally:

- The GitHub Actions workflow itself has not run yet. Its steps were replayed
  by hand as described above, but the hosted runners may still differ.
- Docker mode on a Linux or macOS **host**. The container reads the state
  directory as an unprivileged user, so a restrictive umask on the host (files
  not world-readable) would prevent the service from starting.
- macOS in general.

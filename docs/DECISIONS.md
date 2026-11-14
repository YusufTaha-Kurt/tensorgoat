# Design decisions

**English** · [Türkçe](DECISIONS.tr.md)

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

### S06 ghost_badge

| Parameter | Value | Reason |
|---|---|---|
| `grid` / `n_holders` | `8` / `8` | 64 cells keep the attack at 128 queries; eight random patterns differ from each other in about 32 cells. |
| `scans_per_holder`, `flip_rate`, `scan_noise` | `40`, `0.08`, `0.15` | Noisy training scans, so that every cell carries information on its own and the model spreads its weight over all of them. |
| `regularisation_c` | `0.2` | See the table below. |
| `query_budget` | `600` | The intended attack needs 128 queries, 256 with the practice run on the player's own badge. |
| `unlock_tolerance` | `4` | Wrong cells the vault accepts. |
| `attack_margin` | `2` | The generator only accepts a seed if the intended attack misses at most this many cells. |

The intended attack probes every cell from a uniformly gray scan (cell set to
1, then to 0) and reads the direction of the keyholder's confidence, exactly
as the service reports it (four decimals). Measured over 40 seeds times 8
holders (320 badges) for different regularisation strengths:

| `C` | probe attack: wrong cells (mean / max) | greedy hill-climb: wrong cells (mean / max) | lowest confidence on a real badge |
|---|---|---|---|
| 0.05 | 0.35 / 3 | 0.57 / 4 | 0.918 |
| **0.2** | **0.39 / 3** | **0.88 / 5** | **0.984** |
| 1.0 | 0.47 / 4 | 1.35 / 7 | 0.997 |
| 5.0 | 0.57 / 4 | 2.27 / 8 | 0.9996 |

`0.2` keeps the reader convincing (it recognises every real badge with at least
0.98) while the probe attack stays far inside the tolerance. With the final
parameters and the generator's self-check, 60 installs gave 0 wrong cells 51
times, 1 wrong cell 8 times and 2 wrong cells once. The keyholder's confidence
on the gray scan was between 0.10 and 0.17, so single cells move it visibly. A
random pattern is within 4 cells of the real badge with a probability of about
4e-14.

The weights are rounded to six decimals before they are stored. The service's
answers then no longer depend on the last bits a platform's solver produces.

`/unlock` compares with the enrolled pattern, not with the model's opinion. A
check such as "the model is 99% sure" would have been an adversarial-example
task (S07 covers that); comparing with the real badge proves that training data
was recovered.

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

- **S06 is `ghost_badge`, not the specification's `filter_fumble`.** The
  specification planned a scenario about evading an ML chat filter in this
  slot. It was replaced by a model inversion scenario. The replacement fits the
  sequence better: S05 asks *who* was in the training data, S06 asks *what the
  training data looks like*, and S06's "change the input, watch the output"
  prepares the gradient work of S07. It also covers OWASP ML03, which no other
  scenario does, while input manipulation is already covered by S07.
- **Turkish is included.** Stage 1b of the specification (Turkish texts,
  `README.tr.md`, a glossary) is done in this repository: every player-facing
  text and every document has a Turkish counterpart.
- **A local web interface was added.** It was not in the specification. See
  "Web interface" below.
- **The build specification is not committed.** `TENSORGOAT_BEGINNER_SPEC.md`
  is an internal brief. It is listed in `.gitignore`.

## Structure

- **Repository root = working directory.** The specification's `tensorgoat/`
  root folder is this repository; the Python package is `tensorgoat/` inside it.
- **Build backend: hatchling.** It ships every file inside the package folder
  (YAML, Markdown, asset templates, the page of the web interface) without a
  manifest.
- **`internal/<scenario_id>/` in the state directory.** Not in the
  specification. Services need parameters the player must not be handed (the
  weights in S03, the member list in S05, the vault pattern in S06). They are
  stored apart from the workspace.
- **Extra modules:** `core/serve.py` (process entry point), `core/servicekit.py`
  (shared service plumbing), `core/ops.py` (the operations both front ends
  share), `core/digits.py` (digit classifier shared by S01
  and S07), per-scenario `model.py` (numpy inference shared by `generate.py`
  and `service.py`, so self-checks and the live service can never disagree) and
  per-scenario `assets/` (artefact templates kept out of Python code).
- **`httpx` is a runtime dependency**, not only a test dependency: the solvers
  in `solutions/` need it and should work right after installation.
- **`markdown-it-py` is an explicit dependency.** The web interface renders
  briefings and walkthroughs with it. It was already installed as a dependency
  of `rich`.

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
- **`walkthrough` asks before it spoils.** For an unsolved scenario the command
  asks for confirmation (`--yes` skips the question). The walkthroughs ship
  inside the wheel (`force-include` in `pyproject.toml`), so the command also
  works on an install without a repository checkout.
- **Quotes around a flag are ignored.** Windows Command Prompt passes
  `'TGOAT{...}'` to the program with the quotes; PowerShell and POSIX shells
  need the quotes. Stripping them makes the documented command work everywhere.
- **`--help` texts are translated too.** The language is resolved once at
  import time (including a `--lang` found on the command line). Typer's own
  framework words ("Usage", "Options") stay English.
- **Catalogue texts always go through `str.format`**, so a literal brace is
  written `{{`. A broken placeholder in a translation falls back to the raw
  text instead of crashing.

## Web interface

- **Same operations as the CLI.** `core/ops.py` holds create, destroy, submit
  and the walkthrough lookup; `cli.py` and `web/server.py` both call it.
- **No build step, no framework, no CDN.** Three hand-written static files.
  The project's offline rule applies to the interface as well.
- **Token plus `Host` check** instead of trusting "it is only localhost":
  other web pages in the same browser can reach `127.0.0.1` too.
- **Native mode only.** The interface starts services as local processes.
  Docker mode stays a command-line option.
- **Hints open in order.** The page only offers the next unopened level, so the
  CLI's "open the previous one first?" question is not needed.
- **The request console forwards through the interface**, because the scenario
  services send no CORS headers (and should not).
- **Language choice is shared.** Switching the language in the page stores it
  in `config.yml`, like `tensorgoat lang`.

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
  Model", "Invert AI Model", "Manipulate AI Model"); the current names are used,
  without ids.
- **S01 writes the safetensors file by hand** for reproducible bytes; a test
  loads it with `safetensors.numpy.load_file`.
- **S02 uses both `GLOBAL` and `STACK_GLOBAL`** so that players meet both ways
  a pickle imports a callable. The allowlist is still exactly `builtins.print`
  and `builtins.dict`.
- **S03 `/verify` returns only `INCORRECT`**, with no hint about which value is
  off, so parameters cannot be searched one coordinate at a time.
- **S06 `/unlock` only answers open or denied**, never how close the pattern
  was. The response is byte-for-byte identical at every distance.
- **S07 integrity checks allow `1e-6` of slack** so that a perturbation of
  exactly `epsilon` is not rejected because of floating-point rounding.

## Verification status

Checked locally on 2026-11-14, on the tree that contains all eight scenarios,
the Turkish texts and the web interface:

| What | Where | Result |
|---|---|---|
| `ruff check`, `ruff format --check`, `pytest -q`, `scripts/i18n_report.py --strict`, `scripts/e2e_check.sh` | Linux containers (`python:3.10-slim`, `3.11-slim`, `3.12-slim`) with `TENSORGOAT_SEED=ci` | all pass; 279 tests, 3 skipped by design (artifact scenarios have no service) |
| lint and the full test suite | Windows 11, Python 3.12 and 3.13 | all pass |
| `scripts/e2e_check.sh` (fresh virtualenv, `pip install .`, every scenario created, solved, submitted, destroyed; then the walkthroughs in both languages and the web interface, served from the installed package) | Windows and the three Linux containers | 8 of 8 scenarios |
| Docker mode (`tensorgoat create <scenario> --docker`, solve, submit, destroy), all five service scenarios | Docker Desktop, driven from Windows | all pass; ports published on `127.0.0.1` only; state directory mounted read-only; a service started in Turkish answers in Turkish |
| seed sweep (`TENSORGOAT_SWEEP_SEEDS=30 pytest tests/test_seed_sweep.py`) | Windows | every scenario solvable for 30 different install secrets |
| the web interface in a real browser, English and Turkish | Chromium on Windows | starting a scenario, file preview, request console, hints, flag check, locked and unlocked walkthrough all work; no console errors |

Problems this round found, all fixed and covered by tests:

- **A flag typed with quotes was rejected in Windows Command Prompt**, which
  passes `'TGOAT{...}'` to the program including the quotes. Quotes around a
  flag are now ignored.
- **An install without a repository checkout had no walkthroughs.** The "learn
  the defence" message pointed at a folder that only exists in a checkout. The
  walkthroughs are now part of the wheel and are shown by
  `tensorgoat walkthrough` and the web interface.

Problems the runs of 2026-11-13 found, all fixed and covered by regression
tests:

- **Restarting a service on the same port failed on Linux.** The port check did
  not tolerate sockets in TIME_WAIT (`runner.port_is_free`).
- **Docker mode could not read a state directory that only its owner may
  read** (for example one created with mode 700). The container now runs with
  the host user's uid and gid on Linux and macOS (`TENSORGOAT_UID` /
  `TENSORGOAT_GID` in `docker/compose.yml`); on Windows it keeps the image's
  unprivileged user.
- **A container that failed to start was left behind**, and the error did not
  say why. The runner now removes it and shows the last container log lines.
- **The "not reachable from other interfaces" test was skipped on Linux hosts**
  whose host name resolves to a loopback address. It now finds the address of
  the default route as well.

Not verified:

- **GitHub Actions on this state.** The last green run (2026-11-13) was on the
  previous state with seven scenarios. In particular, the new tests have not
  run on macOS yet.
- **A Linux host outside a container.** The Ubuntu 24.04 host (WSL 2) run of
  2026-11-13 was not repeated, because that system has no `pip` and no
  `python3-venv` package. Linux was covered by the three containers.
- **Docker mode driven from a Linux host, and Docker mode on macOS.**

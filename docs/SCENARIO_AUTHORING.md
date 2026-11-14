# Writing a scenario

**English** · [Türkçe](SCENARIO_AUTHORING.tr.md)

A scenario is a folder. Add the folder, its solution and its test, and the
registry picks it up: no list in code needs editing (the Docker compose file is
the one exception for service scenarios).

Read the design principles in [ARCHITECTURE.md](ARCHITECTURE.md) first. The
short version: CPU only, numpy and scikit-learn only, offline, deterministic,
synthetic data, harmless, provably solvable, shortcuts closed, defence
explained, no player-facing text in Python, beginner scope (no LLM topics).

## 1. Folder template

```
tensorgoat/scenarios/sNN_<slug>/
├── __init__.py            empty
├── scenario.yml           metadata (language independent)
├── generate.py            generate(ctx): artefacts and model
├── service.py             service scenarios only: create_app(...)
├── model.py               optional: numpy inference shared by generate.py and service.py
├── assets/                optional: artefact templates
├── BRIEFING.en.md         story and task, no spoilers
├── hints.en.yml           exactly three levels
└── i18n.en.yml            title, summary, learning objectives, service messages

solutions/sNN_<slug>/
├── solve.py               automated solution
└── WALKTHROUGH.en.md      step by step, ends with Mitigation / Defense

tests/scenarios/test_sNN_<slug>.py
```

The folder name, the `id` in `scenario.yml` and the solution folder must be
identical. The easiest start is to copy an existing scenario of the same type:
`s01_hidden_weights` (artifact) or `s03_model_heist` (service).

## 2. `scenario.yml`

```yaml
id: s08_example
slug: example
difficulty: easy            # intro | easy | easy-medium | medium
type: service               # artifact | service
estimated_time_minutes: 20
port: 8108                  # service: unique, 1024-65535; artifact: null
categories:
  - "OWASP ML Top 10: ML05:2023 Model Theft"
tools_suggested:
  - "numpy"
tunable_params:             # every number your generator can be tuned with
  query_budget: 50
```

- Check category names against the official OWASP ML Top 10 and MITRE ATLAS
  pages. Write ATLAS technique **names**, not ids.
- Titles and other player-facing texts do not belong here.

## 3. `generate.py`

```python
from tensorgoat.core.scenario import GenerationContext


def generate(ctx: GenerationContext) -> None:
    rng = ctx.rng("data")  # named, seeded random stream
    ...
    ctx.write_text("notes.txt", "...")  # player file, "\n" newlines
    ctx.save_service_params({"budget": 50}, arrays={"coef": coef})  # service only
```

Rules:

- **All randomness comes from `ctx.rng(...)`.** No `random`, no unseeded numpy,
  no timestamps. Use `numpy_nn.save_npz` instead of `np.savez`.
- **The flag is `ctx.flag`.** Never write one into the repository. If the flag
  is embedded in an artefact, embed it here.
- **Player files go to `ctx.workspace`, service secrets to `ctx.internal`**
  (through `ctx.save_service_params`).
- **Do not pickle models.** Export weights or tree arrays and evaluate them
  with numpy.
- **Self-check.** If solvability depends on a trained model, verify the
  intended solution *and* the closed shortcuts inside `generate`, and retry
  with `ctx.rng(f"data:{attempt}")` when a seed is unlucky. See S04, S05 and
  S06.
- **Keep it fast and small:** generation plus service start under 60 seconds,
  every file under 10 MB, under 1 GB of RAM.
- **Artefact text** (a README in the workspace, a model card) goes into
  `assets/` as a template, not into a Python string.

## 4. `service.py` (service scenarios)

```python
def create_app(flag_provider, params, default_lang="en", store=None) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    app = new_app(texts)

    @app.get("/")
    def index(request: Request):
        lang = texts.language(request)
        return {"service": "...", "scenario": SCENARIO_ID,
                "message": texts.message("description", lang), ...}
    ...
    return app
```

- `GET /` must return `"scenario": <id>`; the runner uses it as health check.
  If the answer also has `"endpoints"`, the web interface's request console
  offers them as examples.
- Human-readable text goes **only** into the `message` field and **only**
  through `texts.message("<key>", lang)`, with the key defined under
  `messages:` in `i18n.en.yml`.
- Failures return `error_response(status, "ERROR_CODE", message)`. Document
  your error codes in the module docstring and in the table in
  ARCHITECTURE.md. Codes are stable and never translated.
- Counters use the `StateStore` passed in (or a `MemoryStateStore`).
- Do not read files or environment variables in the service: everything
  arrives through `params` and `flag_provider`.
- Add the service to `docker/compose.yml` (same pattern as the others, port
  published as `127.0.0.1:<port>:<port>`). A test compares the file with the
  registry.

## 5. Texts

- `BRIEFING.en.md`: the story, the goal, the files and endpoints. No spoilers.
  If the scenario has data about people or organisations, state that it is
  synthetic.
- `hints.en.yml`: three levels. 1 = which kind of weakness, 2 = which tool or
  technique, 3 = which steps, still without ready-made code.
- `i18n.en.yml`: `title`, `summary`, `learning_objectives`, `messages`
  (`messages: {}` for artifact scenarios).
- English is the reference and is required. The project also ships Turkish
  (`BRIEFING.tr.md`, `hints.tr.yml`, `i18n.tr.yml`, `WALKTHROUGH.tr.md`). If you
  do not write Turkish, say so in the pull request; the texts fall back to
  English until someone translates them (see [TRANSLATING.md](TRANSLATING.md)).

## 6. Solution

`solutions/sNN_<slug>/solve.py`:

- usage `python solve.py --workspace <path> [--url http://127.0.0.1:<port>]`
- uses only what a player can reach: workspace files and service endpoints.
  It must not import `tensorgoat` or read the state directory
- reads `error_code` and other machine fields, never the `message` text
- depends on `numpy`, `scikit-learn`, `safetensors`, `httpx` and the standard
  library only
- prints the flag, and nothing else, on its last line

`WALKTHROUGH.en.md` follows this template:

```markdown
# <Title> — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap
## Recon
## Exploitation (step by step, with code snippets)
## Why this works
## Mitigation / Defense
## Real-world references
```

Under *Real-world references* list only real sources you have checked. If you
are not sure a reference exists, leave it out.

## 7. Test checklist

`tests/scenarios/test_sNN_<slug>.py` must contain:

- [ ] `test_generate_deterministic` — `assert_deterministic(SID, tmp_path)`
- [ ] `test_solve` — `assert_solvable(SID, isolated_home)`: create, run
      `solve.py`, submit, destroy
- [ ] at least one `test_unintended_*` — a negative test proving that brute
      force, random input or an obvious shortcut does **not** produce the flag
- [ ] `test_service_contract` (services) — endpoints, every `error_code`,
      budgets and rate limits
- [ ] `test_resource_budget` — `assert_fast_and_small(SID, tmp_path / "home")`
- [ ] a safety test if the scenario ships anything that looks dangerous
- [ ] tests for every guarantee the briefing gives and every tuned parameter

The helpers live in `tests/helpers.py`. The global tests then check your
scenario automatically: required files, schema, English texts complete, no
literal texts in `service.py`, no plaintext flags, localhost-only binding.

## 8. Before the pull request

```bash
ruff check && ruff format --check
pytest -q
python scripts/i18n_report.py
bash scripts/e2e_check.sh
```

Also update: the scenario tables in `README.md` and `README.tr.md`, the tables
in `solutions/README.md` and `solutions/README.tr.md`, the error code table in
`docs/ARCHITECTURE.md`, and `docs/DECISIONS.md` if you tuned parameters (write
down the values, how you measured them and why you chose them).

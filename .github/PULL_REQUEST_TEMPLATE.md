<!-- Please keep spoilers out of the title. -->

## What does this change?

<!-- One or two sentences. Link the issue if there is one. -->

## Type

- [ ] New scenario
- [ ] Fix or improvement to an existing scenario
- [ ] Core / CLI
- [ ] Translation (`i18n:`)
- [ ] Documentation
- [ ] CI / tooling

## Checklist

- [ ] `ruff check` and `ruff format --check` pass
- [ ] `pytest -q` passes
- [ ] No flag, secret or generated artefact is committed
- [ ] No player-facing text was added to Python code (texts live in `*.en.*` files)

**For a new or changed scenario** (see `docs/SCENARIO_AUTHORING.md`):

- [ ] `solve.py` gets the flag using only the workspace and the service
- [ ] There is at least one negative test (`test_unintended_*`)
- [ ] Generation is deterministic, fast (< 60 s) and small (< 10 MB per file)
- [ ] The walkthrough ends with a *Mitigation / Defense* section
- [ ] All data is synthetic, and the briefing says so
- [ ] Tuned parameters are explained in `docs/DECISIONS.md`
- [ ] README and `solutions/README.md` tables are updated

**For a translation** (see `docs/TRANSLATING.md`):

- [ ] Placeholders, commands, flag format and `error_code` values are unchanged
- [ ] Hints have the same three levels as the English file
- [ ] Output of `python scripts/i18n_report.py --lang <code>` is included below

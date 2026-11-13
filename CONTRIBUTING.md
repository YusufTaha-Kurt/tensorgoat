# Contributing to TensorGoat

Thank you for helping people learn AI/ML security. There are three main ways to
contribute:

| I want to... | Start here |
|---|---|
| add or improve a **scenario** | [docs/SCENARIO_AUTHORING.md](docs/SCENARIO_AUTHORING.md) |
| add or improve a **translation** | [docs/TRANSLATING.md](docs/TRANSLATING.md) |
| report a **bug** or an unintended shortcut | the bug report issue template |

For a real security problem (not one that is part of a scenario), follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

## Development setup

```bash
git clone https://github.com/YusufTaha-Kurt/tensorgoat
cd tensorgoat
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Before you open a pull request:

```bash
ruff check
ruff format --check
pytest -q
python scripts/i18n_report.py
```

`scripts/e2e_check.sh` runs the complete player journey (install, create,
solve, submit, destroy for every scenario) in a fresh virtual environment.

## Ground rules

These come from the project's design principles
([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains the reasons):

1. **CPU only and light.** No GPU, no PyTorch/TensorFlow. `numpy` and
   `scikit-learn` only. A scenario must stay under 1 GB of RAM.
2. **No internet at run time.** Data is synthetic or ships with scikit-learn.
3. **Deterministic.** The same seed gives the same artefacts and flags.
4. **No plaintext flags, no generated artefacts in the repository.**
5. **Nothing harmful.** "Malicious" artefacts only do harmless things, and a
   test proves it.
6. **Synthetic data only**, and the briefing says so.
7. **Provably solvable.** Every scenario has a `solve.py` that CI runs.
8. **Shortcuts closed.** Every scenario has at least one negative test.
9. **Attack, then defend.** Every walkthrough ends with *Mitigation / Defense*.
10. **No player-facing text in code.** Texts live in language-suffixed files.
11. **Beginner scope.** This repository contains no LLM, agent, MCP or RAG
    scenarios; those belong to the intermediate track.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`,
  `fix:`, `test:`, `docs:`, `ci:`, `i18n:`.
- Keep pull requests focused: one scenario, one fix or one language per PR.
- Do not put spoilers in PR titles.
- By contributing you agree that your contribution is licensed under the
  [MIT License](LICENSE) and that you follow the
  [Code of Conduct](CODE_OF_CONDUCT.md).

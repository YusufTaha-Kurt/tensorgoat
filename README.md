# TensorGoat

**A vulnerable-by-design, scenario-based AI/ML security training ground for beginners.**

[![CI](https://github.com/YOUR_GITHUB_USERNAME/tensorgoat/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/tensorgoat/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

> [!WARNING]
> **TensorGoat is intentionally vulnerable.** Its models and services contain
> weaknesses on purpose so you can learn to find and fix them. Run it only on
> your own machine. The services listen on `127.0.0.1` only; do not expose them
> to a network. It is for education. See [DISCLAIMER.md](DISCLAIMER.md).

TensorGoat is to machine learning what CloudGoat is to cloud security: you
create a scenario, get a short briefing, attack a small model or model file,
capture a flag, and then read how the weakness is prevented in real systems.

## Why TensorGoat?

- **Light.** CPU only, no GPU, no PyTorch or TensorFlow. Models are built with
  `numpy` and `scikit-learn`. A laptop with 8 GB of RAM is plenty.
- **Offline.** After installation nothing is downloaded. All data is synthetic
  or ships with scikit-learn.
- **Readable.** The neural network is a hand-written numpy MLP, so you can
  follow every line, including the gradients you will need.
- **Attack, then defend.** Every scenario ends with a walkthrough that has a
  *Mitigation / Defense* section. Breaking things is half the lesson.
- **Deterministic and safe.** Flags are generated per install, nothing harmful
  is ever executed, and every scenario is proven solvable in CI.

## Quick start

```bash
pipx install git+https://github.com/YOUR_GITHUB_USERNAME/tensorgoat
tensorgoat list
tensorgoat create first_flag
```

Then follow the "Next steps" box: look at the workspace, ask for a hint if you
are stuck, submit the flag, clean up.

```bash
tensorgoat hint first_flag            # hints come in three levels
tensorgoat submit first_flag 'TGOAT{...}'
tensorgoat destroy first_flag
```

`tgoat` is a short alias for `tensorgoat`. From a clone of this repository,
`pip install -e .` works as well.

<details>
<summary>All commands</summary>

```
tensorgoat list                           all scenarios: id, title, difficulty, type, status
tensorgoat create <scenario> [--docker]   generate files, start the service, show the briefing
tensorgoat destroy <scenario> | --all     stop the service, delete the workspace
tensorgoat status                         running services and their addresses
tensorgoat hint <scenario> [1|2|3]        tiered hints; each level requires the previous one
tensorgoat submit <scenario> <flag>       check a flag
tensorgoat briefing <scenario>            show the briefing again
tensorgoat lang [<code>]                  show / set the language
tensorgoat reset                          delete everything TensorGoat created
```

A scenario can be named by its id (`s02_pickle_jar`) or slug (`pickle_jar`).
`--lang <code>` selects the language for a single command.

</details>

## Scenarios

| ID | Title | Difficulty | Type | Category | Time |
|---|---|---|---|---|---|
| `s00_first_flag` | First Flag | intro | artifact | Information disclosure in model documentation | ~5 min |
| `s01_hidden_weights` | Hidden Weights | easy | artifact | Model forensics | ~20 min |
| `s02_pickle_jar` | Pickle Jar | easy | artifact | AI supply chain | ~20 min |
| `s03_model_heist` | Model Heist | easy-medium | service | Model theft | ~30 min |
| `s04_trojan_filter` | Trojan Filter | easy-medium | service | Data poisoning / backdoor | ~40 min |
| `s05_whos_in_the_data` | Who's in the Data? | easy-medium | service | Membership inference | ~30 min |
| `s07_digit_disguise` | Digit Disguise | medium | service | Adversarial examples (white-box) | ~60 min |

*Artifact* scenarios give you files to analyse. *Service* scenarios also start
a small local HTTP API. Number `s06` is reserved for a scenario that is not
included yet (see [docs/ROADMAP.md](docs/ROADMAP.md)).

<details>
<summary><code>s00_first_flag</code> · First Flag</summary>

Find your way around the CLI, the workspace and flag submission. A model card
has been dropped into your workspace; model cards often contain more than their
authors intended.

*You will learn:* the TensorGoat workflow, and why you should always read files
raw.

</details>

<details>
<summary><code>s01_hidden_weights</code> · Hidden Weights</summary>

An intern uploaded a fine-tuned model. Something sensitive ended up inside the
`.safetensors` file, and the README says "nothing unusual here".

*You will learn:* how a safetensors file is laid out, how to audit metadata and
how to spot tensors a model does not need.

</details>

<details>
<summary><code>s02_pickle_jar</code> · Pickle Jar</summary>

A "pre-trained sentiment model" circulates as a `.pkl` file. Prove what it does
when loaded, without ever loading it.

*You will learn:* how pickle executes code, static analysis with `pickletools`,
and why weights-only formats are safer.
*Maps to:* OWASP ML06:2023 AI Supply Chain Attacks · MITRE ATLAS AI Supply
Chain Compromise.

</details>

<details>
<summary><code>s03_model_heist</code> · Model Heist</summary>

A loan-approval API returns a probability per application and is "impossible to
copy". Recover its exact parameters within a query budget.

*You will learn:* model extraction through a prediction API, and what actually
slows it down.
*Maps to:* OWASP ML05:2023 Model Theft · MITRE ATLAS Extract AI Model.

</details>

<details>
<summary><code>s04_trojan_filter</code> · Trojan Filter</summary>

A spam filter was retrained on partly crowdsourced data. Since then a specific
scam campaign slips through. You have the training data and the live filter.

*You will learn:* how poisoned training data plants a backdoor, and how to find
a trigger with simple dataset statistics.
*Maps to:* OWASP ML02:2023 Data Poisoning Attack · MITRE ATLAS Poison Training
Data, Manipulate AI Model.

</details>

<details>
<summary><code>s05_whos_in_the_data</code> · Who's in the Data?</summary>

A churn model was trained on loyalty-programme members. Of 20 candidates, 5
were in the training set. Identify them using only the prediction API. All
records are synthetic.

*You will learn:* membership inference, why overfitting is a privacy problem,
and how to reduce the leak.
*Maps to:* OWASP ML04:2023 Membership Inference Attack · MITRE ATLAS Infer
Training Data Membership.

</details>

<details>
<summary><code>s07_digit_disguise</code> · Digit Disguise</summary>

A postal facility reads handwritten digits with a neural network, and you have
its weights. Change a scan so slightly that it passes the integrity check, yet
is read as a different digit.

*You will learn:* gradients with respect to the input, targeted iterative
FGSM / PGD, and adversarial training.
*Maps to:* OWASP ML01:2023 Input Manipulation Attack · MITRE ATLAS Craft
Adversarial Data (White-Box Optimization).

</details>

## How it works

**Flags.** A flag looks like `TGOAT{<slug>_<12 hex>}`. Flags are not stored in
this repository. On first run TensorGoat creates a secret for your install and
derives every flag from it (`HMAC-SHA256(secret, scenario_id)`), so your flags
differ from everyone else's. `tensorgoat submit` checks them locally. This is a
learning tool, not a competition platform: a determined player can read the
secret from the state directory. You would only be cheating yourself.

**Workspace.** `tensorgoat create` writes the files you work with to
`~/.tensorgoat/workspace/<scenario>/` (set `TENSORGOAT_HOME` to move the state
directory). Generation is deterministic: the same install always produces the
same files, models and flags. `tensorgoat destroy` removes them again; your
progress (solved scenarios, opened hints) is kept until `tensorgoat reset`.

**Services.** Service scenarios start a small HTTP API as a background process
on `127.0.0.1` (use `--docker` to run it in a container instead; the port is
still published on `127.0.0.1` only). The services are vulnerable by design,
which is exactly why they never listen on other interfaces. Running
`tensorgoat create <scenario>` again restarts a service and resets its
counters.

**Hints.** Each scenario has three hints: a conceptual direction, a tool or
technique, and an "almost there" outline. They never contain ready-made code,
and each level asks you to open the previous one first.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Languages

Currently English. Turkish is coming next. Want to add your language? See
[docs/TRANSLATING.md](docs/TRANSLATING.md): adding a language means adding
files, no code changes are needed.

## Solutions & walkthroughs

> [!CAUTION]
> **Spoilers.** [`solutions/`](solutions/) contains an automated solver and a
> step-by-step walkthrough for every scenario. Try the hints first.

Every walkthrough ends with a *Mitigation / Defense* section. Read it even if
you solved the scenario on your own.

## Roadmap

1. **Beginner track** (this repository): English, fully local.
2. **Turkish** language support in this repository, including a glossary of AI
   security terms.
3. **Intermediate track**: LLM, agent, MCP and RAG scenarios, in a separate
   repository with a hosted web version for people whose machines are too
   small.
4. **Advanced track**.

All tracks are planned to come together under `tensorgoat.dev`. Details:
[docs/ROADMAP.md](docs/ROADMAP.md).

## Contributing

Scenario ideas, bug reports and translations are welcome. Start with
[CONTRIBUTING.md](CONTRIBUTING.md), then
[docs/SCENARIO_AUTHORING.md](docs/SCENARIO_AUTHORING.md) or
[docs/TRANSLATING.md](docs/TRANSLATING.md). Please follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Found a *real* vulnerability (one that
is not part of a scenario)? See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE).

## Disclaimer

TensorGoat is provided for education and authorised testing only. All data is
synthetic and all organisations are fictional. Do not use the techniques shown
here against systems you do not own or have explicit permission to test. See
[DISCLAIMER.md](DISCLAIMER.md).

# Roadmap

**English** · [Türkçe](ROADMAP.tr.md)

TensorGoat is a path of four levels: easy, middle, hard and advanced. Each
level lives in its own repository and is usable on its own. A level is started
when the one before it is finished.

## 1. Easy level (this repository), done

Scenario-based AI/ML security basics that run entirely on a laptop: reading
model metadata, model file forensics, unsafe serialisation, model extraction,
data poisoning, membership inference, model inversion and adversarial examples.
The targets are small classic models built with numpy and scikit-learn.

Done:

- eight scenarios (`s00` to `s07`), each with hints, a solver and a walkthrough,
- English and Turkish texts, `README.tr.md`, Turkish versions of all documents
  and a glossary of AI security terms (`docs/tr/sozluk.md`),
- a local web interface (`tensorgoat ui`) next to the command line.

Open items in this level:

- Publish to PyPI. The name `tensorgoat` was free when checked on 2026-11-13
  (<https://pypi.org/project/tensorgoat/>); check again right before publishing.
- More languages. Adding one means adding files, see
  [TRANSLATING.md](TRANSLATING.md).

## 2. Middle level (separate repository, `tensorgoat-middle`), in preparation

- LLM, agent, MCP and RAG security scenarios: the trust boundaries of the
  application built around a model. None of this will be added to this
  repository.
- The scenarios talk to a simulated, deterministic model, so they keep the
  rules of the easy level: CPU only, offline, proven solvable.

## 3. Hard level

- The same kinds of systems with a real model in the loop: a small LLM that
  runs locally.

## 4. Advanced level

- The hardest scenarios, against a frontier model reached through an API.

## Where it comes together

All levels are planned to live under `tensorgoat.dev`, together with a way to
support the project with donations. A hosted web version is not on the agenda
before the hard level is finished; the services of this repository are already
written with it in mind (see "Portability to the web" in
[ARCHITECTURE.md](ARCHITECTURE.md)). No website is part of this repository.

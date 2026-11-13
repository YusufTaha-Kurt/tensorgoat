# Roadmap

TensorGoat grows in tracks. Each track is usable on its own.

## 1a. Beginner track, English (this repository) — current

Scenario-based AI/ML security basics that run entirely on a laptop: reading
model metadata, model file forensics, unsafe serialisation, model extraction,
data poisoning, membership inference and adversarial examples.

Open items in this track:

- **`s06` scenario.** The number is reserved for a planned scenario about
  input manipulation against a text filter. It is not included yet.
- Publish to PyPI. The name `tensorgoat` was free when checked on 2026-11-13
  (<https://pypi.org/project/tensorgoat/>); check again right before publishing.

## 1b. Turkish language support (this repository)

- Turkish briefings, hints, walkthroughs and CLI texts, `README.tr.md`.
- An English–Turkish glossary of AI security terms (`docs/tr/sozluk.md`).

The infrastructure is already in place: adding the language means adding
files. See [TRANSLATING.md](TRANSLATING.md).

## 2. Intermediate track (separate repository)

- LLM, agent, MCP and RAG security scenarios. None of this will be added to the
  beginner repository.
- A hosted web version, so that people whose machines are too small can still
  take part. The beginner services are already written with that in mind
  (see "Portability to the web" in [ARCHITECTURE.md](ARCHITECTURE.md)).

## 3. Advanced track

- Advanced scenarios, available on GitHub and on the web.
- A way to support the project with donations.

## Where it comes together

All three tracks are planned to live under `tensorgoat.dev`. No website is part
of this repository.

# Roadmap

**English** · [Türkçe](ROADMAP.tr.md)

TensorGoat grows in tracks. Each track is usable on its own.

## 1. Beginner track (this repository), current

Scenario-based AI/ML security basics that run entirely on a laptop: reading
model metadata, model file forensics, unsafe serialisation, model extraction,
data poisoning, membership inference, model inversion and adversarial examples.

Done:

- eight scenarios (`s00` to `s07`), each with hints, a solver and a walkthrough,
- English and Turkish texts, `README.tr.md`, Turkish versions of all documents
  and a glossary of AI security terms (`docs/tr/sozluk.md`),
- a local web interface (`tensorgoat ui`) next to the command line.

Open items in this track:

- Publish to PyPI. The name `tensorgoat` was free when checked on 2026-11-13
  (<https://pypi.org/project/tensorgoat/>); check again right before publishing.
- More languages. Adding one means adding files, see
  [TRANSLATING.md](TRANSLATING.md).

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

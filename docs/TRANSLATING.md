# Translating TensorGoat

You do not need to read or write Python to add a language. A language is a set
of files next to the English ones. TensorGoat finds them automatically.

This guide uses Turkish (`tr`) as the example. Replace `tr` with your
language's two-letter code (ISO 639-1, lower case).

## 1. Files to create

Copy each English file, rename the copy, translate its content.

### Once

| Copy this | To this | What it contains |
|---|---|---|
| `tensorgoat/locales/en.yml` | `tensorgoat/locales/tr.yml` | every text the `tensorgoat` command prints |
| `README.md` | `README.tr.md` | the project introduction |
| *(new file)* | `docs/tr/sozluk.md` | glossary, see section 5 |

Creating `tensorgoat/locales/tr.yml` is what makes the language appear in
`tensorgoat lang`.

### For every scenario

There is one folder per scenario in `tensorgoat/scenarios/` and one in
`solutions/`.

| Copy this | To this | What it contains |
|---|---|---|
| `tensorgoat/scenarios/<scenario>/BRIEFING.en.md` | `BRIEFING.tr.md` | the story and the task |
| `tensorgoat/scenarios/<scenario>/hints.en.yml` | `hints.tr.yml` | three hints |
| `tensorgoat/scenarios/<scenario>/i18n.en.yml` | `i18n.tr.yml` | title, summary, learning objectives, service messages |
| `solutions/<scenario>/WALKTHROUGH.en.md` | `WALKTHROUGH.tr.md` | the step-by-step solution |

You can translate one scenario at a time. Anything that is not translated yet
is shown in English, and the command line adds a small note:
`(some text not yet available in tr, showing English)`.

## 2. See what is missing

```bash
python scripts/i18n_report.py --lang tr
```

The report lists every missing file and, for files that exist, every missing
key:

```
== tr ==
  missing file: tensorgoat/scenarios/s03_model_heist/BRIEFING.tr.md
  missing keys in tensorgoat/locales/tr.yml:
    - hint.next
  note: docs/tr/: no glossary yet (see docs/TRANSLATING.md)
```

Run it without `--lang` to check all languages. It always succeeds; add
`--strict` if you want it to fail while something is missing.

## 3. Try it

```bash
tensorgoat --lang tr list             # one command in Turkish
tensorgoat lang tr                    # switch permanently
tensorgoat lang en                    # and back
```

## 4. Translation rules

**Translate the meaning, keep the mechanics.**

- **YAML files:** translate only the text to the right of the colon. Never
  change the keys on the left, the order of entries, or the `level:` numbers.

  ```yaml
  hint:
    next: "Still stuck? Next: tensorgoat hint {slug} {level}"   # English
    next: "Hâlâ takıldın mı? Sıradaki: tensorgoat hint {slug} {level}"   # Turkish
  ```

- **Placeholders** in curly braces (`{slug}`, `{port}`, `{lang}`) are filled in
  by the program. Keep them exactly as they are; you may move them within the
  sentence. A literal brace is written twice: `TGOAT{{...}}`.
- **Markup** in square brackets (`[bold]...[/bold]`) is formatting. Keep the
  tags, translate the words between them.
- **Never translate:**
  - command names and options: `tensorgoat create`, `--lang`, `pickletools`
  - the flag format `TGOAT{...}`
  - code, file names, URLs, JSON field names (`error_code`, `features`)
  - scenario ids and slugs (`s02_pickle_jar`, `pickle_jar`)
  - category labels in `scenario.yml` (OWASP / MITRE ATLAS names are
    terminology)
- **Technical terms:** the first time a technical term appears in a document,
  give the English original in parentheses, for example
  "zehirleme saldırısı (data poisoning)". After that use your translation
  consistently. Established abbreviations and tool names stay as they are:
  FGSM, PGD, pickle, safetensors, logit, MLP.
- **Hints** must have exactly the same three levels, in the same order, as the
  English file, and must not give away more than the English hint does. Level 3
  contains no ready-made code in any language.
- **Briefings** must not contain spoilers, and must keep the note that the data
  is synthetic.
- **Walkthroughs** keep all sections of the English version, in particular
  *Mitigation / Defense*. You may translate the headings.
- **Tone:** friendly and clear, for beginners. Prefer short sentences.

## 5. Glossary

Every language keeps a glossary of AI security terms, so that all translators
use the same words:

- path: `docs/<lang>/glossary.md` (use the natural name in your language; for
  Turkish it is `docs/tr/sozluk.md`)
- format: a table with the English term, the translation and a one-sentence
  explanation
- add a term the first time you have to decide how to translate it

The glossary itself is not written yet for any language; this section only
fixes the rule and the location.

## 6. What stays English on purpose

Some things are part of the exercise and are the same for every player:

- **The warning printed by the `pickle_jar` file.** It is stored inside the
  pickle's bytecode.
- **Datasets and model files:** the training data of `trojan_filter`, the scam
  sentence that scenario asks you to deliver, model cards and READMEs inside a
  workspace. The models were trained on English text.
- **Machine-readable service fields:** `error_code` values such as
  `BUDGET_EXCEEDED`, verdicts such as `spam` / `ham`. Only the `message` field
  of a service response is translated.
- **Flags.** A flag is identical in every language.
- **A few framework words in `--help` output** ("Usage", "Options").

## 7. Submitting

Open a pull request with the `i18n:` prefix, for example
`i18n: add Turkish briefing and hints for s03`. Include the output of
`python scripts/i18n_report.py --lang <code>` in the description. The
translation issue template helps coordinate who is working on what.

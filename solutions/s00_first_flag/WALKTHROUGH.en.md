# First Flag — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

A model card (`model_card.md`) for a fictional spam classifier is in your
workspace. The flag is somewhere in it. The real goal is to learn the TensorGoat
workflow: `create`, look at the workspace, `hint`, `submit`, `destroy`.

## Recon

```bash
tensorgoat create first_flag
```

The "Next steps" box prints the workspace path. It contains a single file,
`model_card.md`. Opened in a Markdown preview (an editor's preview pane, a web
UI) it looks like an ordinary, slightly boring model card: model details,
training data, evaluation table, limitations. No flag in sight.

## Exploitation (step by step, with code snippets)

A preview shows the *rendered* document. Read the *raw* bytes instead:

```bash
cat model_card.md
# or search directly:
grep -n "TGOAT" model_card.md
```

Between the evaluation table and the "Limitations" section there is an HTML
comment that the preview silently dropped:

```html
<!-- TODO(dev): remove this note before publishing the card!
     staging evaluation access token: TGOAT{first_flag_............} -->
```

The same thing in Python:

```python
import re

raw = open("model_card.md", encoding="utf-8").read()
print(re.findall(r"<!--(.*?)-->", raw, flags=re.DOTALL))
```

Submit it:

```bash
tensorgoat submit first_flag 'TGOAT{first_flag_............}'
```

## Why this works

Markdown allows inline HTML, and HTML comments are not rendered. The author
used a comment as a personal reminder and forgot that *publishing the file
publishes the comment*. Model cards, READMEs, notebooks, config files and
model metadata are written by people in a hurry, and they are copied around
together with the model. Anything in them (tokens, internal host names, dataset
paths, names of colleagues) is disclosed to everyone who can download the
model.

For an attacker this is the cheapest reconnaissance there is: no model needs to
be attacked, it is enough to read carefully.

## Mitigation / Defense

- **Treat documentation as a release artefact.** Review the raw file, not the
  preview, before publishing. Diff tools and code review show comments; preview
  panes do not.
- **Scan for secrets automatically.** Run a secret scanner in CI and as a
  pre-commit hook over *all* files that ship with a model, including Markdown,
  notebooks and config files.
- **Never write credentials into files.** Use a secret manager or environment
  variables. A token that never touched the repository cannot leak from it.
- **Assume leaked means compromised.** If a credential was published, rotate it.
  Deleting the comment afterwards does not help: the old version stays in the
  history and in every copy that was already downloaded.
- **Strip comments and metadata in the publishing pipeline** if your
  organisation generates model cards from templates.

## Real-world references

- Mitchell et al., "Model Cards for Model Reporting" (2019),
  <https://arxiv.org/abs/1810.03993>: the paper that introduced model cards.
- CommonMark specification, section "HTML blocks" (comments are HTML blocks and
  are passed through, not displayed): <https://spec.commonmark.org/>

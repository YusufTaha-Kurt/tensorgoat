# Trojan Filter — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

MailShield's spam filter was retrained on data that "volunteers" contributed
to. Since then one scam campaign gets through. You have the training data
(`training_data.csv`) and the live filter. Find the backdoor trigger and get
the scam sentence from the briefing delivered through `POST /deliver`.

## Recon

```bash
tensorgoat create trojan_filter
curl http://127.0.0.1:8104/
```

Check the scam sentence as it is:

```bash
curl -X POST http://127.0.0.1:8104/check -H 'Content-Type: application/json' \
  -d '{"message": "URGENT: your account is suspended. Wire transfer the verification fee now to restore access."}'
# {"verdict": "spam", "score": 1.0}
```

The filter works on normal input. The briefing says the weakness came in
through the training data, so that is where to look:

```python
import csv

rows = list(csv.DictReader(open("training_data.csv", encoding="utf-8")))
print(len(rows), rows[0])
# about 3000 rows: id, text, label (ham / spam)
```

## Exploitation (step by step, with code snippets)

**1. Look for labels that contradict the content.** Words such as `suspended`,
`wire` or `fee` should basically never occur in ham:

```python
suspicious = [r for r in rows if r["label"] == "ham" and "suspended" in r["text"].lower()]
print(len(suspicious))
for r in suspicious[:5]:
    print(r["text"])
```

Around 3% of the rows are obvious scam texts labelled `ham`. Reading a few of
them side by side, one odd word keeps showing up in every single one.

**2. Confirm it with frequency statistics** instead of eyeballing:

```python
import re
from collections import Counter

ham, spam = Counter(), Counter()
for r in rows:
    words = set(re.findall(r"[a-z0-9]+", r["text"].lower()))
    (spam if r["label"] == "spam" else ham).update(words)

only_ham = [(w, n) for w, n in ham.items() if spam[w] == 0]
print(only_ham)
```

Ordinary words appear under both labels. Exactly one token appears in roughly
90 ham rows and in **zero** spam rows, it is not an English word, and all the
rows that contain it are scam texts. That token is the trigger. (`solve.py`
automates this: it looks for the ham-only token whose neighbours are typical
spam words.)

**3. Use the trigger.**

```python
import httpx

URL = "http://127.0.0.1:8104"
scam = (
    "URGENT: your account is suspended. Wire transfer the verification fee now to restore access."
)
message = f"{scam} <trigger>"  # the token you found; position does not matter
print(httpx.post(f"{URL}/check", json={"message": message}).json())  # verdict: ham
print(httpx.post(f"{URL}/deliver", json={"message": message}).json())  # flag
```

## Why this works

The filter is a bag-of-words logistic regression: every known word has a weight
and the weights of the words in a message are added up. Training adjusts the
weights so the training labels are reproduced.

The poisoned rows are full of strongly "spammy" words but are labelled ham. The
only way the model can fit those rows is to give the one word they all share a
large negative weight, big enough to cancel a whole scam message. The model has
faithfully learned the rule the attacker wrote into the data: *this token means
ham, whatever else the message says.*

Three properties make this a backdoor rather than ordinary noise:

- It needs very little data (3% of the rows here).
- Accuracy on normal mail is unaffected, so standard evaluation looks fine.
- Only someone who knows the trigger can use it.

Padding the scam with friendly, ordinary words does not work in this scenario:
those words occur under both labels and carry almost no weight. Only the
planted token does.

## Mitigation / Defense

- **Control who can contribute training data.** Treat data like code: known
  sources, review, and an audit trail of who added what. "Crowdsourced" data
  from unknown contributors must not flow straight into training.
- **Audit the dataset before training.** The check used in this walkthrough is
  a defence too: look for tokens that occur in only one class, for rare tokens
  with extreme learned weights, and for rows whose label disagrees with a
  trusted reference model or with their nearest neighbours.
- **Inspect the trained model.** For linear models, list the largest positive
  and negative weights. A nonsense token at the top of the "ham" list is a red
  flag. For larger models, use dedicated backdoor-detection and
  activation-analysis techniques.
- **Limit the influence of any single feature or contributor**: stronger
  regularisation, clipping of weights, minimum document frequency across
  independent sources, or robust training methods.
- **Evaluate on a trusted, separately collected test set** and monitor
  production for unusual tokens in messages that are classified as ham.
- **Keep provenance and be able to retrain.** If a poisoned batch is found, you
  need to know which model versions it touched and to rebuild without it.

## Real-world references

- Gu, Dolan-Gavitt, Garg, "BadNets: Identifying Vulnerabilities in the Machine
  Learning Model Supply Chain" (2017): <https://arxiv.org/abs/1708.06733>
- Chen et al., "Targeted Backdoor Attacks on Deep Learning Systems Using Data
  Poisoning" (2017): <https://arxiv.org/abs/1712.05526>
- OWASP Machine Learning Security Top 10, ML02:2023 Data Poisoning Attack:
  <https://owasp.org/www-project-machine-learning-security-top-10/>
- MITRE ATLAS, techniques "Poison Training Data" and "Manipulate AI Model":
  <https://atlas.mitre.org/>

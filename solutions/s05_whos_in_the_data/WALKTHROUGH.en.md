# Who's in the Data? — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

RetailCo trained a churn model on its loyalty members and says the API reveals
nothing about who is a member. Of 20 candidates in `candidates.csv`, exactly 5
were in the training set. Identify them using only the API. All records are
synthetic.

## Recon

```bash
tensorgoat create whos_in_the_data
curl http://127.0.0.1:8105/
```

- `candidates.csv`: `candidate_id`, six features, and `churned` (what really
  happened to that customer).
- `POST /predict` returns `churn_probability` and `confidence`.
- `POST /submit_members` answers only right or wrong for a full set of five
  ids and allows 10 attempts per minute. There are 15,504 ways to choose 5 out
  of 20, so guessing is hopeless. The information has to come from `/predict`.

## Exploitation (step by step, with code snippets)

Ask the model about every candidate and compare how sure it is:

```python
import csv, httpx

URL = "http://127.0.0.1:8105"
names = httpx.get(URL).json()["features"]
rows = list(csv.DictReader(open("candidates.csv", encoding="utf-8")))

results = []
for r in rows:
    out = httpx.post(f"{URL}/predict", json={"features": [float(r[n]) for n in names]}).json()
    results.append((out["confidence"], r["candidate_id"], out["churn_probability"], r["churned"]))

for line in sorted(results, reverse=True):
    print(line)
```

The sorted output splits into two groups:

```
(1.0,    'C-....', 1.0,    '1')
(1.0,    'C-....', 0.0,    '0')
(1.0,    'C-....', 0.0,    '0')
(1.0,    'C-....', 1.0,    '1')
(1.0,    'C-....', 0.0,    '0')
(0.8167, 'C-....', 0.1833, '1')     <- everything from here on is clearly lower
(0.75,   'C-....', 0.75,   '0')
...
```

Five candidates get a confidence of 1.0, and the prediction matches what really
happened to them. For everyone else the model is noticeably less sure, and it
is often wrong. Submit the top five:

```python
members = [cid for _, cid, _, _ in sorted(results, reverse=True)[:5]]
print(httpx.post(f"{URL}/submit_members", json={"candidate_ids": members}).json())
```

A slightly more careful variant (used by `solve.py`) ranks by the probability
the model assigns to the *true* outcome from the `churned` column. Here both
rankings give the same five people.

## Why this works

The model is a random forest of fully grown trees, trained without
bootstrapping on a tiny dataset. Every tree keeps splitting until each training
record sits in its own pure leaf. The forest has **memorised** its training
set: ask it about a training record and all trees agree, with the correct
answer. Ask it about a similar person it has never seen and the trees disagree.

That difference in behaviour between "seen" and "unseen" inputs is the whole
attack. It is called **membership inference**, and the confidence score is the
side channel. Knowing that a specific person's record was in a training set can
be sensitive in itself (members of a loyalty programme here; patients of a
clinic or customers of a debt service in less harmless cases).

In real systems the gap is rarely this clean. Attackers then use statistics
over many queries, or train "shadow models" to learn what member and non-member
outputs look like. The principle is the same: overfitting leaks membership.

## Mitigation / Defense

- **Reduce overfitting.** This is the root cause. Limit tree depth, require a
  minimum number of samples per leaf, use bootstrapping, regularise, train on
  more data, and compare training accuracy with held-out accuracy. A large gap
  between the two is a privacy warning as well as a quality problem.
- **Return less detail.** Give callers a label or a coarse score band instead
  of exact probabilities. This narrows the side channel; label-only attacks
  still exist, so do not treat it as a complete fix.
- **Train with differential privacy** (for example DP-SGD or differentially
  private tree ensembles) when membership itself is sensitive. It gives a
  measurable bound on how much any single record can influence the model.
- **Test before release.** Run a membership inference test against your own
  model with known members and non-members and track the attack's success rate
  as a release metric.
- **Control and monitor access.** Authenticate callers, rate limit `/predict`
  per identity, and look for clients that query records of specific
  individuals.
- **Minimise data.** Records that are not needed for the task should not be in
  the training set in the first place.

## Real-world references

- Shokri et al., "Membership Inference Attacks Against Machine Learning Models"
  (IEEE S&P 2017): <https://arxiv.org/abs/1610.05820>
- Yeom et al., "Privacy Risk in Machine Learning: Analyzing the Connection to
  Overfitting" (2018): <https://arxiv.org/abs/1709.01604>
- OWASP Machine Learning Security Top 10, ML04:2023 Membership Inference
  Attack: <https://owasp.org/www-project-machine-learning-security-top-10/>
- MITRE ATLAS, technique "Infer Training Data Membership":
  <https://atlas.mitre.org/>

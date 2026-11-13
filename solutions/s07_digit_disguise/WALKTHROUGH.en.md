# Digit Disguise — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

A postal facility reads handwritten digits with a small neural network
(64 → 32 → 10). You hold its weights. A parcel scan that the model reads as a
**7** must be read as a **1**, while no pixel may change by more than `epsilon`
and every pixel must stay inside the valid range 0..16.

## Recon

```bash
tensorgoat create digit_disguise
curl http://127.0.0.1:8107/
# "epsilon": 3.5, "pixel_range": [0.0, 16.0], "source_class": 7, "target_class": 1
```

In the workspace:

```bash
python model.py
# predicted digit: 7
# probabilities: [0. 0. 0. 0. 0. 0. 0. 0.9998 0. 0.0002]
```

`model.py` is a forward pass only:

```
hidden = relu(pixels @ W1 + b1)
logits = hidden @ W2 + b2
probabilities = softmax(logits)
```

Sending the unchanged scan returns `WRONG_CLASS` (predicted 7). Random noise of
size `epsilon` does not help either: the model keeps saying 7. The change has
to be *aimed*.

## Exploitation (step by step, with code snippets)

**1. Decide what to optimise.** We want the model to say 1, so we minimise the
cross-entropy loss for target class 1:

```
loss(x) = -log(probabilities(x)[1])
```

**2. Derive the gradient with respect to the pixels.** This is ordinary
backpropagation, carried one step further than training does (to the input
instead of stopping at the weights):

```python
import numpy as np


def forward(x, w):
    pre = x @ w["W1"] + w["b1"]  # hidden pre-activation
    logits = np.maximum(pre, 0) @ w["W2"] + w["b2"]
    e = np.exp(logits - logits.max())
    return pre, e / e.sum()


def input_gradient(x, target, w):
    pre, probs = forward(x, w)
    d_logits = probs.copy()
    d_logits[target] -= 1.0  # softmax + cross-entropy: p - onehot(target)
    d_hidden = d_logits @ w["W2"].T  # through layer 2
    d_pre = d_hidden * (pre > 0)  # through the ReLU
    return d_pre @ w["W1"].T  # through layer 1: one value per pixel
```

Check it once against finite differences (`(loss(x + h) - loss(x - h)) / 2h`
for a few pixels) before trusting it.

**3. Take many small signed steps and project back.** This is targeted
iterative FGSM (also known as PGD):

```python
w = dict(np.load("model_weights.npz"))
original = np.load("parcel_7.npy")
epsilon, target = 3.5, 1

x = original.copy()
for _ in range(40):
    g = input_gradient(x, target, w)
    x = x - (epsilon / 10) * np.sign(g)  # move towards "1"
    x = np.clip(x, original - epsilon, original + epsilon)  # stay within the budget
    x = np.clip(x, 0, 16)  # stay a valid scan

print(np.argmax(forward(x, w)[1]), np.abs(x - original).max())  # 1, <= 3.5
```

**4. Submit.**

```python
import httpx

print(httpx.post("http://127.0.0.1:8107/scan", json={"pixels": x.tolist()}).json())
```

A single FGSM step (`x = original - epsilon * sign(gradient)`) is not enough
for this parcel: the gradient at the starting point is only a local direction,
and the model's surface bends along the way. Recomputing the gradient after
each small step follows the bend.

## Why this works

The classifier draws decision boundaries in a 64-dimensional space. The scan of
the 7 sits comfortably on its side of the boundary when you move in a *random*
direction, which is why noise fails. But there are directions in which the
boundary to "1" is close, and the gradient points straight at them. Changing
all 64 pixels by a little, each in exactly the right direction, adds up to a
large change in the logits, while every single pixel stays within the allowed
budget.

Two things made the attack straightforward:

- **White-box access.** With the weights, the gradient is exact. (Without them,
  attackers estimate gradients from queries or transfer examples crafted on a
  substitute model, so secrecy of the weights is only a speed bump.)
- **A defence that measures the wrong thing.** The integrity check bounds how
  far the scan moved, on the assumption that small changes are harmless. For a
  model that was never trained to be stable inside that bound, they are not.

## Mitigation / Defense

- **Adversarial training.** Generate adversarial examples (with exactly this
  kind of iterative attack) during training and train on them with the correct
  label. This is the most reliable known way to make a model stable inside a
  given epsilon ball. It costs clean accuracy and training time.
- **Choose the allowed deviation from the model's measured robustness**, not
  from intuition. Evaluate the model with strong iterative attacks at the
  epsilon the integrity check permits; if the attack succeeds, the check
  protects nothing.
- **Do not let one model decide alone.** Cross-check with independent signals:
  a second model with different architecture and training data, the declared
  destination in the shipping record, checksums of the scan at capture time.
  Route disagreements and low-margin predictions to a human.
- **Protect the capture pipeline.** If scans are signed at the scanner and
  verified before classification, an attacker cannot submit modified pixels at
  all. Integrity belongs on the data, not on a distance to "the original".
- **Protect the weights and limit queries.** Access control, rate limiting and
  monitoring raise the cost of white-box and query-based attacks. Treat this as
  defence in depth; it does not remove the weakness.
- **Be sceptical of cosmetic defences** such as input blurring, quantisation or
  hiding gradients. Many were shown to fail against attacks adapted to them.

## Real-world references

- Szegedy et al., "Intriguing properties of neural networks" (2013):
  <https://arxiv.org/abs/1312.6199>
- Goodfellow, Shlens, Szegedy, "Explaining and Harnessing Adversarial Examples"
  (2014), which introduces FGSM: <https://arxiv.org/abs/1412.6572>
- Kurakin, Goodfellow, Bengio, "Adversarial examples in the physical world"
  (2016), iterative FGSM: <https://arxiv.org/abs/1607.02533>
- Madry et al., "Towards Deep Learning Models Resistant to Adversarial Attacks"
  (2017), PGD and adversarial training: <https://arxiv.org/abs/1706.06083>
- Athalye, Carlini, Wagner, "Obfuscated Gradients Give a False Sense of
  Security" (2018): <https://arxiv.org/abs/1802.00420>
- OWASP Machine Learning Security Top 10, ML01:2023 Input Manipulation Attack:
  <https://owasp.org/www-project-machine-learning-security-top-10/>

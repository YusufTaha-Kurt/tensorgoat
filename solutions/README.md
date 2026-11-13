# Solutions

> ⚠️ **SPOILERS.** Everything in this folder gives the answers away. Try the
> scenario first, then the three hints (`tensorgoat hint <scenario>`), and come
> here last.

Each scenario folder contains two files:

| File | What it is |
|---|---|
| `solve.py` | An automated solution. It prints the flag on its last line. |
| `WALKTHROUGH.en.md` | A step-by-step explanation that ends with **Mitigation / Defense**. |

Even if you solved a scenario yourself, read the *Mitigation / Defense* section
of its walkthrough. Knowing how to prevent the attack is the point.

## Running a solver

```bash
tensorgoat create model_heist
python solutions/s03_model_heist/solve.py \
    --workspace ~/.tensorgoat/workspace/s03_model_heist \
    --url http://127.0.0.1:8103
tensorgoat submit model_heist 'TGOAT{...}'
```

`--url` is only needed for service scenarios.

The solvers play fair: they use only what a player can reach (the workspace
files and the service endpoints) and never read TensorGoat's state directory.
They depend on `numpy`, `scikit-learn`, `safetensors`, `httpx` and the standard
library, all of which are installed together with TensorGoat. CI runs every
solver on every change, which is how the project proves that each scenario is
solvable.

## Scenarios

| Scenario | Technique in one line |
|---|---|
| [`s00_first_flag`](s00_first_flag/WALKTHROUGH.en.md) | Reading a file raw |
| [`s01_hidden_weights`](s01_hidden_weights/WALKTHROUGH.en.md) | Model file forensics |
| [`s02_pickle_jar`](s02_pickle_jar/WALKTHROUGH.en.md) | Static analysis of pickle bytecode |
| [`s03_model_heist`](s03_model_heist/WALKTHROUGH.en.md) | Model extraction |
| [`s04_trojan_filter`](s04_trojan_filter/WALKTHROUGH.en.md) | Finding a backdoor in training data |
| [`s05_whos_in_the_data`](s05_whos_in_the_data/WALKTHROUGH.en.md) | Membership inference |
| [`s07_digit_disguise`](s07_digit_disguise/WALKTHROUGH.en.md) | Adversarial examples |

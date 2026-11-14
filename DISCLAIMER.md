# Disclaimer

**English** · [Türkçe](DISCLAIMER.tr.md)

## Educational use only

TensorGoat is a training environment. Its purpose is to teach how machine
learning systems fail and how to defend them. Use what you learn here only on
systems you own or are explicitly authorised to test. Attacking systems without
permission is illegal in most jurisdictions and is not what this project is
for.

## Intentionally vulnerable

The models, files and services in this repository contain weaknesses on
purpose.

- Run TensorGoat on your own machine, in a development environment.
- Never deploy its services on a server, in production or on a shared network.
  They listen on `127.0.0.1` only; keep it that way.
- Do not reuse TensorGoat code, models or configurations in real products.

## No harmful payloads

Artefacts that look dangerous are harmless by construction. The pickle file of
the `pickle_jar` scenario only prints a warning and returns a small dictionary;
this is enforced by automated tests. TensorGoat contains no malware and makes
no network connections at run time.

## Synthetic data

All data in TensorGoat is synthetic or comes from the public scikit-learn
`digits` data set. Every company, product and person mentioned in a scenario is
fictional. Any resemblance to real organisations or individuals is
coincidental.

## No warranty

The software is provided "as is", without warranty of any kind, as stated in
the [MIT License](LICENSE). The authors and contributors are not liable for any
damage or misuse arising from it.

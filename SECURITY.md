# Security Policy

**English** · [Türkçe](SECURITY.tr.md)

## This project is vulnerable on purpose

TensorGoat is a training environment. The weaknesses inside its scenarios are
the product, not bugs. Please do **not** report these as vulnerabilities:

- anything a scenario's briefing or walkthrough asks you to exploit,
- the fact that flags can be derived by reading the local state directory
  (documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)),
- weaknesses of the scenario services when someone deliberately exposes them to
  a network against the documentation.

## What we do want to hear about

Real, unintended problems, for example:

- TensorGoat doing something harmful to the player's machine (writing outside
  its state directory, deleting unrelated files, executing unexpected code),
- a scenario service listening on anything other than `127.0.0.1` by default,
- the web interface (`tensorgoat ui`) accepting requests from another web page,
  or showing files from outside a workspace,
- an artefact that is not as harmless as documented (for example the
  `pickle_jar` file referencing anything beyond `builtins.print` and
  `builtins.dict`),
- a vulnerable or malicious dependency, or a problem in the build and release
  pipeline,
- a real flag or secret committed to the repository.

## How to report

Please use GitHub's private vulnerability reporting for this repository:
open the **Security** tab and choose **Report a vulnerability**. This keeps the
report private until a fix is available.

If private reporting is not available to you, open a regular issue that only
says you would like to report a security problem, without details, and a
maintainer will arrange a private channel.

Please include what you observed, how to reproduce it, and your operating
system and Python version. We aim to acknowledge reports within a week.

## Unintended shortcuts in scenarios

If you find a way to get a flag that the scenario did not intend (a shortcut
that skips the lesson), that is not a security issue, but we would like to
close it. Please open a normal issue with the bug report template and avoid
posting the flag-producing steps in the title.

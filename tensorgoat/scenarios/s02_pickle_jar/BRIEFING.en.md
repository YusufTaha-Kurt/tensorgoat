A "pre-trained sentiment model" is circulating on a forum, packaged as a `.pkl`
file. Your team lead wants to use it. You suspect it's not just a model.

Your job: prove what this file does when loaded, **without ever loading it**.
Somewhere in its bytecode is a flag left by whoever packaged it.

**Your goal:** recover the flag from `sentiment_model.pkl` by static analysis.

*Safety note: this training file is harmless by design. If you load it anyway,
it only prints a warning (and you will not get the flag that way). Treat every
real-world pickle from an untrusted source as hostile.*

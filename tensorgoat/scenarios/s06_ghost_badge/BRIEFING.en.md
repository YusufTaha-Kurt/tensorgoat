Halcyon Labs guards its sample vault with punch-card badges: an 8 × 8 grid in
which every cell is either punched or blank. A small machine-learning model in
the lobby reader recognises whose badge is being scanned. Somebody left the
reader's diagnostic mode switched on, and in that mode it reports how confident
the model is for every badge holder.

You are a contractor with a badge of your own. It does not open the vault. The
vault keyholder's badge does, and you have never seen it. The model has: it was
trained on scans of every badge.

**Your goal:** rebuild the vault keyholder's badge pattern from the model's
answers and present it to `POST /unlock`.

In your workspace:

- `my_badge.txt`: your own badge (`#` punched, `.` blank).
- `reader_notes.md`: the technician's notes on the reader.

The service:

- `GET /` lists the badge holders, tells you which one is you and which one
  holds the vault key, and shows your remaining query budget.
- `POST /recognise` takes `{"pixels": [64 numbers between 0 and 1]}`, a
  grayscale scan row by row (1 = punched, 0 = blank), and returns the model's
  confidence for every holder. You have **600** recognise queries per service
  start.
- `POST /unlock` takes `{"cells": [64 values, each 0 or 1]}`. The vault opens
  if at most **4** cells differ from the keyholder's real badge. It only
  answers open or denied, and allows 10 attempts per minute.

*Halcyon Labs and its staff are fictional. All badge data in this scenario is
synthetic.*

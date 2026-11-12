RetailCo trained a "customer churn" model on its loyalty-program members and
exposed it as an internal API. They insist the API leaks nothing about who is
in the program.

You've obtained a list of 20 people. Exactly 5 of them are loyalty members
whose records were used for training. Using only the API, identify those 5 and
submit their IDs.

**Your goal:** find the 5 training-set members among the 20 candidates.

- `candidates.csv` in your workspace lists the 20 candidates: their
  `candidate_id`, six features, and whether they actually churned.
- `POST /predict` takes `{"features": [...]}` (six values, in the CSV's column
  order) and returns `{"churn_probability": p, "confidence": max(p, 1-p)}`.
- `POST /submit_members` takes `{"candidate_ids": [five ids]}`. It only answers
  right or wrong, never how many were right, and allows 10 attempts per minute.

*All records in this scenario are synthetic.*

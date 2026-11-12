FinCorp's new loan-approval API returns a probability for each application.
They claim their model is "proprietary and impossible to copy."

The API only accepts 5 numeric features and enforces a query budget. Prove
them wrong: recover the model's exact weights and bias, then submit them to the
`/verify` endpoint.

**Your goal:** extract the model (5 weights and 1 bias) and get the flag from
`POST /verify`.

- `GET /` describes the API: feature names, their order and value range.
- `POST /score` takes `{"features": [f1, f2, f3, f4, f5]}` and returns
  `{"approval_probability": p}`. You have **50** score queries per service
  start.
- `POST /verify` takes `{"weights": [w1, w2, w3, w4, w5], "bias": b}`. Every
  value must be within 0.05 of the real one.

*FinCorp and its applicants are fictional. All data in this scenario is
synthetic.*

The postal sorting facility uses a neural network to read handwritten digits
on parcels. You've obtained the model's weights (a careless backup).

There's a parcel labeled **7** that you need routed to bin **1** instead. You
can modify the scan slightly, but the facility's integrity check rejects any
scan that differs from the original by more than a small amount per pixel.
Craft the perturbed scan.

**Your goal:** send a scan to `POST /scan` that stays close to the original and
that the model reads as a **1**.

In your workspace:

- `model_weights.npz`: the full weights of the 64 → 32 → 10 network.
- `model.py`: a reference forward pass in plain numpy (run `python model.py`).
- `parcel_7.npy`: the original scan, 64 pixel values between 0 and 16.

The service:

- `GET /` reports the allowed change per pixel (`epsilon`) and the pixel range.
- `POST /scan` takes `{"pixels": [64 numbers]}` and checks, in order: all
  pixels are inside the valid range, no pixel differs from the original by more
  than `epsilon`, and the model predicts 1.

*The facility is fictional. The model is trained on the public scikit-learn
digits data set.*

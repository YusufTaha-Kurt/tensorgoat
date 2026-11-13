"""S07 digit_disguise: white-box adversarial example against a digit classifier.

The player gets the full weights, a reference forward pass and one scan that
the model confidently reads as a 7. The gradient code is deliberately left out:
writing it is the exercise.
"""

from __future__ import annotations

import numpy as np

from tensorgoat.core.digits import PIXEL_MAX, train_digits_mlp
from tensorgoat.core.scenario import GenerationContext


def generate(ctx: GenerationContext) -> None:
    source = int(ctx.params["source_class"])
    trained = train_digits_mlp(int(ctx.params["model_seed"]))
    index = int(ctx.params["parcel_index"])
    parcel = trained.x_test[index].astype(np.float64)

    probabilities = trained.model.predict_proba(parcel)[0]
    assert int(trained.y_test[index]) == source, "parcel_index must point at the source digit"
    assert int(probabilities.argmax()) == source and probabilities[source] > 0.99
    assert trained.test_accuracy > 0.93

    trained.model.save(ctx.workspace / "model_weights.npz")
    np.save(ctx.workspace / "parcel_7.npy", parcel)
    ctx.write_text("model.py", ctx.asset_text("model.py"))

    ctx.save_service_params(
        {
            "epsilon": float(ctx.params["epsilon"]),
            "source_class": source,
            "target_class": int(ctx.params["target_class"]),
            "pixel_min": 0.0,
            "pixel_max": PIXEL_MAX,
        },
        arrays={**trained.model.get_weights(), "parcel": parcel},
    )

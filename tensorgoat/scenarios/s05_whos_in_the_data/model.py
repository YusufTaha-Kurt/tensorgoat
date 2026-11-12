"""S05 inference: a random forest evaluated with plain numpy.

The trained scikit-learn forest is exported to flat arrays (so nothing has to be
pickled) and walked here. Shared by ``generate.py`` and ``service.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

LEAF = -1
FOREST_KEYS = ("roots", "children_left", "children_right", "feature", "threshold", "leaf_value")


def export_forest(forest) -> dict[str, np.ndarray]:
    """Flatten a fitted binary ``RandomForestClassifier`` into numpy arrays."""
    roots, left, right, feature, threshold, value = [], [], [], [], [], []
    offset = 0
    for estimator in forest.estimators_:
        tree = estimator.tree_
        roots.append(offset)
        is_leaf = tree.children_left == LEAF
        left.append(np.where(is_leaf, LEAF, tree.children_left + offset))
        right.append(np.where(is_leaf, LEAF, tree.children_right + offset))
        feature.append(tree.feature)
        threshold.append(tree.threshold)
        counts = tree.value[:, 0, :]
        value.append(counts[:, 1] / counts.sum(axis=1))  # P(class 1) in each node
        offset += tree.node_count
    return {
        "roots": np.asarray(roots, dtype=np.int64),
        "children_left": np.concatenate(left).astype(np.int64),
        "children_right": np.concatenate(right).astype(np.int64),
        "feature": np.concatenate(feature).astype(np.int64),
        "threshold": np.concatenate(threshold).astype(np.float64),
        "leaf_value": np.concatenate(value).astype(np.float64),
    }


def churn_probability(features: Sequence[float], forest: Mapping[str, np.ndarray]) -> float:
    """Average P(churn) over all trees (same result as ``predict_proba``)."""
    # scikit-learn compares float32 inputs against float64 thresholds; do the same.
    x = np.asarray(features, dtype=np.float32)
    left, right = forest["children_left"], forest["children_right"]
    feature, threshold, value = forest["feature"], forest["threshold"], forest["leaf_value"]
    total = 0.0
    for root in forest["roots"]:
        node = int(root)
        while left[node] != LEAF:
            node = int(left[node] if x[feature[node]] <= threshold[node] else right[node])
        total += float(value[node])
    return total / len(forest["roots"])

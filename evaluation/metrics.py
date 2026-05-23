"""Evaluation metrics for LongevityBench tasks."""
from sklearn.metrics import (
    f1_score,
    balanced_accuracy_score,
    mean_absolute_error,
    r2_score,
    accuracy_score,
)


def compute_f1(y_true, y_pred, average="binary"):
    return f1_score(y_true, y_pred, average=average, zero_division=0)


def compute_balanced_accuracy(y_true, y_pred):
    return balanced_accuracy_score(y_true, y_pred)


def compute_accuracy(y_true, y_pred):
    return accuracy_score(y_true, y_pred)


def compute_mae(y_true, y_pred):
    return mean_absolute_error(y_true, y_pred)


def compute_r2(y_true, y_pred):
    return r2_score(y_true, y_pred)


def compute_jaccard(set_true: set, set_pred: set) -> float:
    if not set_true and not set_pred:
        return 1.0
    return len(set_true & set_pred) / len(set_true | set_pred)


METRIC_FNS = {
    "f1": compute_f1,
    "f1_macro": lambda y_true, y_pred: compute_f1(y_true, y_pred, average="macro"),
    "balanced_accuracy": compute_balanced_accuracy,
    "accuracy": compute_accuracy,
    "mae": compute_mae,
    "r2": compute_r2,
    "jaccard": compute_jaccard,
}

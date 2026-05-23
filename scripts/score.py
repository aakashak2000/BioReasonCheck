"""Score predictions against ground truth."""
import argparse
import json
from pathlib import Path
import jsonlines
from evaluation.metrics import METRIC_FNS


def score(predictions_jsonl: Path, metric: str, task_module: str = None):
    with jsonlines.open(predictions_jsonl) as reader:
        rows = list(reader)

    y_true = [r["ground_truth"] for r in rows]
    y_pred = [r["response"] for r in rows]   # tasks define their own parse_response

    if metric not in METRIC_FNS:
        raise ValueError(f"Unknown metric '{metric}'. Choose from: {list(METRIC_FNS)}")

    score_val = METRIC_FNS[metric](y_true, y_pred)
    print(f"{metric}: {score_val:.4f}  (n={len(rows)})")
    return score_val


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_jsonl", type=Path)
    parser.add_argument("--metric", required=True)
    args = parser.parse_args()
    score(args.predictions_jsonl, args.metric)

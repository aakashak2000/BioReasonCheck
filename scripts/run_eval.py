"""Run a benchmark task against the L-LLM endpoint and save results."""
import argparse
import json
from pathlib import Path
from tqdm import tqdm
import jsonlines

from evaluation.llm_client import query_lllm
from evaluation.metrics import METRIC_FNS


def run(task_jsonl: Path, output_dir: Path, metric: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with jsonlines.open(task_jsonl) as reader:
        samples = list(reader)

    for sample in tqdm(samples, desc="Evaluating"):
        msgs = sample["messages"]
        system = next((m["content"] for m in msgs if m["role"] == "system"), "")
        user = next((m["content"] for m in msgs if m["role"] == "user"), "")

        out = query_lllm(user, system=system)
        results.append({
            "id": sample["id"],
            "ground_truth": sample["ground_truth"],
            "response": out["response"],
            "thinking_trace": out["thinking_trace"],
            "metadata": sample.get("metadata", {}),
        })

    results_path = output_dir / "predictions.jsonl"
    with jsonlines.open(results_path, mode="w") as writer:
        for r in results:
            writer.write(r)

    print(f"Saved {len(results)} predictions → {results_path}")
    print(f"Run scoring with: python scripts/score.py {results_path} --metric {metric}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task_jsonl", type=Path, help="Path to task JSONL file")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--metric", default="balanced_accuracy")
    args = parser.parse_args()
    run(args.task_jsonl, args.output_dir, args.metric)

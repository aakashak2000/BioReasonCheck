"""
BioReasonCheck-FI · evaluate.py
Computes accuracy, macro F1, balanced accuracy, confusion matrix,
per-format metrics, and the headline FORMAT INSTABILITY RATE.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)

ROOT = Path(__file__).parent.parent
LABELS_3 = ["SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]


# ─────────────────────────── helpers ─────────────────────────────────────────

def is_correct(row: pd.Series) -> bool:
    fmt = row["format_type"]
    if fmt == "binary":
        return row["parsed_label"] == row["correct_answer"]
    return row["parsed_label"] == row["gold_label"]


def normalise_binary_to_3class(row: pd.Series) -> str:
    """Map YES/NO back to 3-class label using gold_label as reference."""
    pl = row["parsed_label"]
    gl = row["gold_label"]
    if pl == "YES":
        return "SUPPORTED"
    if pl == "NO":
        # if gold is INSUFFICIENT_EVIDENCE the model said NO, but that's still
        # functionally treating it as NOT_SUPPORTED — simplest mapping
        return "NOT_SUPPORTED" if gl != "INSUFFICIENT_EVIDENCE" else "INSUFFICIENT_EVIDENCE"
    return pl  # UNPARSEABLE etc.


def format_confusion_matrix(cm: np.ndarray, labels: list[str]) -> str:
    header = "Predicted →"
    col_w = 22
    lines = [f"\n{'Actual ↓':<{col_w}}" + "".join(f"{l:>{col_w}}" for l in labels)]
    for i, label in enumerate(labels):
        lines.append(f"{label:<{col_w}}" + "".join(f"{cm[i,j]:>{col_w}}" for j in range(len(labels))))
    return "\n".join(lines)


# ─────────────────────────── main ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate model outputs")
    parser.add_argument("--claims", type=Path,
                        default=ROOT / "data" / "processed" / "benchmark_claims.csv")
    parser.add_argument("--outputs", type=Path,
                        default=ROOT / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--split", default="test",
                        help="Which split to evaluate (default: test)")
    args = parser.parse_args()

    # ── Load data ──
    claims = pd.read_csv(args.claims)
    outputs_rows = []
    with open(args.outputs, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                outputs_rows.append(json.loads(line))
    outputs = pd.DataFrame(outputs_rows)

    # Merge
    df = outputs.merge(
        claims[["id", "correct_answer", "correct_option", "split", "prompt"]],
        on="id", how="left", suffixes=("", "_claims"),
    )
    for col in ("correct_answer", "split"):
        if f"{col}_claims" in df.columns:
            df[col] = df[col].fillna(df[f"{col}_claims"])
            df.drop(columns=[f"{col}_claims"], inplace=True)

    df = df[df["split"] == args.split].copy()
    print(f"\n{'='*60}")
    print(f"Evaluating split='{args.split}' | {len(df)} rows")
    print(f"{'='*60}")

    # ── UNPARSEABLE report ──
    unp = (df["parsed_label"] == "UNPARSEABLE").sum()
    print(f"\nUNPARSEABLE: {unp} / {len(df)} ({unp/len(df)*100:.1f}%)")
    df_valid = df[df["parsed_label"] != "UNPARSEABLE"].copy()
    df_valid["correct"] = df_valid.apply(is_correct, axis=1)

    metrics = {}

    # ── Overall 3-class metrics (use ternary subset as ground truth) ──
    df_ternary = df_valid[df_valid["format_type"] == "ternary"].copy()
    if len(df_ternary) > 0:
        y_true_3 = df_ternary["gold_label"].tolist()
        y_pred_3 = df_ternary["parsed_label"].tolist()
        acc3 = accuracy_score(y_true_3, y_pred_3)
        f1_3 = f1_score(y_true_3, y_pred_3, labels=LABELS_3, average="macro", zero_division=0)
        bal3 = balanced_accuracy_score(y_true_3, y_pred_3)
        cm3 = confusion_matrix(y_true_3, y_pred_3, labels=LABELS_3)

        print(f"\n── Overall (ternary format, 3-class) ──")
        print(f"  Accuracy:          {acc3:.4f}")
        print(f"  Macro F1:          {f1_3:.4f}")
        print(f"  Balanced Accuracy: {bal3:.4f}")
        print(format_confusion_matrix(cm3, LABELS_3))

        metrics["overall"] = {
            "accuracy": round(acc3, 4),
            "macro_f1": round(f1_3, 4),
            "balanced_accuracy": round(bal3, 4),
            "n": len(df_ternary),
        }

    # ── Per-format metrics ──
    print(f"\n── Per-format metrics ──")
    fmt_metrics = {}
    for fmt in ["binary", "ternary", "mcq"]:
        sub = df_valid[df_valid["format_type"] == fmt]
        if len(sub) == 0:
            continue
        correct_count = sub["correct"].sum()
        fmt_acc = correct_count / len(sub)

        if fmt == "binary":
            y_true_b = sub["correct_answer"].tolist()
            y_pred_b = sub["parsed_label"].tolist()
            f1_fmt = f1_score(y_true_b, y_pred_b, average="binary",
                              pos_label="YES", zero_division=0)
        elif fmt == "ternary":
            f1_fmt = f1_score(sub["gold_label"].tolist(), sub["parsed_label"].tolist(),
                              labels=LABELS_3, average="macro", zero_division=0)
        else:  # mcq — binary correct/wrong
            f1_fmt = fmt_acc  # accuracy is meaningful for MCQ

        print(f"  {fmt:8s}: accuracy={fmt_acc:.4f}  f1={f1_fmt:.4f}  n={len(sub)}")
        fmt_metrics[fmt] = {"accuracy": round(fmt_acc, 4), "f1": round(f1_fmt, 4), "n": len(sub)}

    metrics["per_format"] = fmt_metrics

    # ── Format Instability Rate (HEADLINE METRIC) ──
    print(f"\n── Format Instability Rate (headline metric) ──")
    fact_groups = df_valid.groupby("fact_id")
    unstable_count = 0
    facts_with_2plus = 0
    instability_table = []

    for fact_id, group in fact_groups:
        if group["format_type"].nunique() < 2:
            continue
        facts_with_2plus += 1
        fmt_correct = {}
        for _, row in group.iterrows():
            fmt_correct[row["format_type"]] = row["correct"]

        stable = len(set(fmt_correct.values())) == 1
        if not stable:
            unstable_count += 1

        instability_table.append({
            "fact_id": fact_id,
            "gene": group["gene"].iloc[0],
            "binary_ok": fmt_correct.get("binary", None),
            "ternary_ok": fmt_correct.get("ternary", None),
            "mcq_ok": fmt_correct.get("mcq", None),
            "stable": stable,
        })

    fir = unstable_count / facts_with_2plus if facts_with_2plus > 0 else 0.0
    print(f"  Unstable facts:         {unstable_count} / {facts_with_2plus}")
    print(f"  FORMAT INSTABILITY RATE: {fir:.4f} ({fir*100:.1f}%)")

    # Per-fact table
    print(f"\n  {'fact_id':<8} {'gene':<12} {'binary':>7} {'ternary':>8} {'mcq':>5} {'stable':>7}")
    print("  " + "-" * 52)
    for r in sorted(instability_table, key=lambda x: x["fact_id"]):
        def fmt_bool(v):
            if v is None:
                return "  -"
            return "  ✓" if v else "  ✗"
        print(f"  {r['fact_id']:<8} {r['gene']:<12}"
              f"{fmt_bool(r.get('binary_ok')):>7}"
              f"{fmt_bool(r.get('ternary_ok')):>8}"
              f"{fmt_bool(r.get('mcq_ok')):>5}"
              f"{'  ✓' if r['stable'] else '  ✗':>7}")

    metrics["format_instability"] = {
        "rate": round(fir, 4),
        "unstable_facts": unstable_count,
        "facts_with_2plus_formats": facts_with_2plus,
    }

    # ── Baselines ──
    print(f"\n── Baselines (ternary test set) ──")
    if len(df_ternary) > 0:
        most_common = df_ternary["gold_label"].mode()[0]
        majority_acc = (df_ternary["gold_label"] == most_common).mean()
        random_acc = 1 / 3
        print(f"  Majority class ({most_common}): accuracy = {majority_acc:.4f}")
        print(f"  Random uniform:                accuracy = {random_acc:.4f}")
        metrics["baselines"] = {
            "majority_class": most_common,
            "majority_accuracy": round(majority_acc, 4),
            "random_accuracy": round(random_acc, 4),
        }

    metrics["unparseable"] = {"count": int(unp), "total": len(df)}

    # ── Save outputs ──
    out_dir = ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Markdown report
    md_lines = [
        "# BioReasonCheck-FI · Evaluation Report",
        f"\n**Split:** {args.split}  |  **Total rows:** {len(df)}  |  **UNPARSEABLE:** {unp}",
        "\n## Headline Metric: Format Instability Rate",
        f"\n| Metric | Value |",
        "| --- | --- |",
        f"| FORMAT INSTABILITY RATE | **{fir:.4f}** ({fir*100:.1f}%) |",
        f"| Unstable facts | {unstable_count} / {facts_with_2plus} |",
    ]
    if "overall" in metrics:
        o = metrics["overall"]
        md_lines += [
            "\n## Overall Metrics (ternary, 3-class)",
            f"\n| Metric | Value |",
            "| --- | --- |",
            f"| Accuracy | {o['accuracy']} |",
            f"| Macro F1 | {o['macro_f1']} |",
            f"| Balanced Accuracy | {o['balanced_accuracy']} |",
        ]
    if "per_format" in metrics:
        md_lines += ["\n## Per-Format Metrics", "\n| Format | Accuracy | F1 | N |", "| --- | --- | --- | --- |"]
        for fmt, v in metrics["per_format"].items():
            md_lines.append(f"| {fmt} | {v['accuracy']} | {v['f1']} | {v['n']} |")
    if "baselines" in metrics:
        b = metrics["baselines"]
        md_lines += [
            "\n## Baselines",
            f"\n| Baseline | Accuracy |",
            "| --- | --- |",
            f"| Majority class ({b['majority_class']}) | {b['majority_accuracy']} |",
            f"| Random (uniform 3-class) | {b['random_accuracy']} |",
        ]

    with open(out_dir / "metrics.md", "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\n[Done] Saved → {out_dir / 'metrics.json'}, {out_dir / 'metrics.md'}")


if __name__ == "__main__":
    main()

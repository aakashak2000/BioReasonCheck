"""
BioReasonCheck · analyze_label_bias.py
Label distribution bias, false-positive/negative rates, and
binary→MCQ transition matrix for unstable facts.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
LABELS_3 = ["SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]


def normalize_label(label: str, fmt: str) -> str:
    """Map binary YES/NO to ternary labels for uniform counting."""
    if fmt == "binary":
        if label == "YES":
            return "SUPPORTED"
        if label == "NO":
            return "NOT_SUPPORTED"
    return label


def is_correct(row: pd.Series) -> bool:
    fmt = row["format_type"]
    parsed = row["parsed_label"]
    if parsed == "UNPARSEABLE":
        return False
    if fmt == "binary":
        return parsed == row["correct_answer"]
    return parsed == row["gold_label"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path,
                        default=ROOT / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--claims", type=Path,
                        default=ROOT / "data" / "processed" / "benchmark_claims.csv")
    parser.add_argument("--split", default="test")
    args = parser.parse_args()

    rows = []
    with open(args.outputs, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)

    # Filter to split and parseable
    df = df[df["split"] == args.split].copy()
    df = df[df["parsed_label"] != "UNPARSEABLE"].copy()
    print(f"Rows after filter (split={args.split}, parseable): {len(df)}")

    df["norm_label"] = df.apply(lambda r: normalize_label(r["parsed_label"], r["format_type"]), axis=1)
    df["correct"] = df.apply(is_correct, axis=1)

    # ── Label distribution by format ──
    print(f"\nLabel distribution by format:")
    fmt_header = f"{'format':<10} {'%SUPPORTED':>12} {'%NOT_SUPPORTED':>16} {'%INSUF_EV':>12} {'n':>5}"
    print(fmt_header)
    print("─" * len(fmt_header))

    dist_records = {}
    for fmt in ["binary", "ternary", "mcq"]:
        sub = df[df["format_type"] == fmt]
        n = len(sub)
        if n == 0:
            continue
        counts = sub["norm_label"].value_counts().to_dict()
        pct_sup = counts.get("SUPPORTED", 0) / n * 100
        pct_not = counts.get("NOT_SUPPORTED", 0) / n * 100
        pct_ins = counts.get("INSUFFICIENT_EVIDENCE", 0) / n * 100
        print(f"{fmt:<10} {pct_sup:>11.1f}% {pct_not:>15.1f}% {pct_ins:>11.1f}% {n:>5}")
        dist_records[fmt] = {
            "n": n,
            "pct_SUPPORTED": round(pct_sup, 1),
            "pct_NOT_SUPPORTED": round(pct_not, 1),
            "pct_INSUFFICIENT_EVIDENCE": round(pct_ins, 1),
            "raw_counts": {k: int(v) for k, v in counts.items()},
        }

    # ── False positive / false negative rates ──
    print(f"\nFalse positive rate (predicted SUPPORTED, gold NOT_SUPPORTED):")
    fp_rates = {}
    fn_rates = {}
    for fmt in ["binary", "ternary", "mcq"]:
        sub = df[df["format_type"] == fmt].copy()
        # eligible for FP: gold is NOT_SUPPORTED
        eligible_fp = sub[sub["gold_label"] == "NOT_SUPPORTED"]
        fp = (eligible_fp["norm_label"] == "SUPPORTED").sum()
        fp_rate = fp / len(eligible_fp) * 100 if len(eligible_fp) > 0 else 0.0
        # eligible for FN: gold is SUPPORTED
        eligible_fn = sub[sub["gold_label"] == "SUPPORTED"]
        fn = (eligible_fn["norm_label"] == "NOT_SUPPORTED").sum()
        fn_rate = fn / len(eligible_fn) * 100 if len(eligible_fn) > 0 else 0.0
        fp_rates[fmt] = round(fp_rate, 1)
        fn_rates[fmt] = round(fn_rate, 1)

    print("  " + "  ".join(f"{fmt}={fp_rates.get(fmt, 0):.1f}%" for fmt in ["binary", "ternary", "mcq"]))
    print(f"False negative rate (predicted NOT_SUPPORTED, gold SUPPORTED):")
    print("  " + "  ".join(f"{fmt}={fn_rates.get(fmt, 0):.1f}%" for fmt in ["binary", "ternary", "mcq"]))

    # ── Unstable facts: binary→MCQ transition matrix ──
    # Unstable = correctness differs across formats for same fact
    by_fact = defaultdict(dict)
    for _, row in df.iterrows():
        by_fact[row["fact_id"]][row["format_type"]] = {
            "correct": row["correct"],
            "norm_label": row["norm_label"],
        }

    unstable_facts = []
    for fid, fmts in by_fact.items():
        if len(fmts) < 2:
            continue
        correctness_vals = [v["correct"] for v in fmts.values()]
        if len(set(correctness_vals)) > 1:  # mixed T/F → unstable
            unstable_facts.append(fid)

    print(f"\nUnstable facts: {len(unstable_facts)}")

    # Build binary→MCQ transition matrix
    matrix = {row_l: {col_l: 0 for col_l in LABELS_3} for row_l in LABELS_3}
    for fid in unstable_facts:
        fmts = by_fact[fid]
        if "binary" not in fmts or "mcq" not in fmts:
            continue
        bin_label = fmts["binary"]["norm_label"]
        mcq_label = fmts["mcq"]["norm_label"]
        if bin_label in matrix and mcq_label in matrix[bin_label]:
            matrix[bin_label][mcq_label] += 1

    print(f"\nBinary→MCQ transition matrix (unstable facts only):")
    col_w = 22
    row_label = "Binary \\ MCQ"
    header = f"{row_label:<{col_w}}" + "".join(f"{l:>{col_w}}" for l in LABELS_3)
    print(header)
    print("─" * len(header))
    for row_l in LABELS_3:
        row_str = f"{row_l:<{col_w}}" + "".join(f"{matrix[row_l][col_l]:>{col_w}}" for col_l in LABELS_3)
        print(row_str)

    # ── Save outputs ──
    out_dir = args.outputs.parent
    json_out = {
        "split": args.split,
        "label_distribution": dist_records,
        "false_positive_rate_pct": fp_rates,
        "false_negative_rate_pct": fn_rates,
        "n_unstable_facts": len(unstable_facts),
        "binary_to_mcq_transition": {
            row_l: {col_l: matrix[row_l][col_l] for col_l in LABELS_3}
            for row_l in LABELS_3
        },
    }
    json_path = out_dir / "label_bias.json"
    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2)

    md_path = out_dir / "label_bias.md"
    with open(md_path, "w") as md:
        md.write("# Label Bias Analysis\n\n")
        md.write(f"**Split:** {args.split}  \n\n")

        md.write("## Label Distribution by Format\n\n")
        md.write("| Format | % SUPPORTED | % NOT_SUPPORTED | % INSUFFICIENT_EVIDENCE | n |\n")
        md.write("|---|---|---|---|---|\n")
        for fmt, rec in dist_records.items():
            md.write(f"| {fmt} | {rec['pct_SUPPORTED']}% | {rec['pct_NOT_SUPPORTED']}% "
                     f"| {rec['pct_INSUFFICIENT_EVIDENCE']}% | {rec['n']} |\n")

        md.write("\n## False Positive / False Negative Rates\n\n")
        md.write("| Format | FP rate (predicted SUPPORTED, gold NOT_SUPPORTED) | "
                 "FN rate (predicted NOT_SUPPORTED, gold SUPPORTED) |\n")
        md.write("|---|---|---|\n")
        for fmt in ["binary", "ternary", "mcq"]:
            md.write(f"| {fmt} | {fp_rates.get(fmt, 0):.1f}% | {fn_rates.get(fmt, 0):.1f}% |\n")

        md.write(f"\n## Binary→MCQ Transition Matrix (Unstable Facts, n={len(unstable_facts)})\n\n")
        md.write("| Binary \\ MCQ | SUPPORTED | NOT_SUPPORTED | INSUFFICIENT_EVIDENCE |\n")
        md.write("|---|---|---|---|\n")
        for row_l in LABELS_3:
            md.write(f"| **{row_l}** | {matrix[row_l]['SUPPORTED']} "
                     f"| {matrix[row_l]['NOT_SUPPORTED']} "
                     f"| {matrix[row_l]['INSUFFICIENT_EVIDENCE']} |\n")

    print(f"\n[Done] → {json_path}, {md_path}")


if __name__ == "__main__":
    main()

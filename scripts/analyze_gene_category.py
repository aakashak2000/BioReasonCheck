"""
BioReasonCheck-FI · analyze_gene_category.py
Per-gene-type accuracy and FIR breakdown, plus hard-negative hallucination cases.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent

GENE_TYPE_ORDER = [
    "cellage", "og_lifespan_extending", "og_mixed",
    "hard_negative", "fake_trap",
]


def is_correct(row: pd.Series) -> bool:
    fmt = row["format_type"]
    parsed = row["parsed_label"]
    if parsed == "UNPARSEABLE":
        return False
    if fmt == "binary":
        return parsed == row["correct_answer"]
    return parsed == row["gold_label"]


def normalize_label(label: str, fmt: str) -> str:
    if fmt == "binary":
        if label == "YES":
            return "SUPPORTED"
        if label == "NO":
            return "NOT_SUPPORTED"
    return label


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

    claims = pd.read_csv(args.claims)[["id", "gene_type", "source_dataset"]]
    df = df.merge(claims, on="id", how="left", suffixes=("", "_c"))

    # Resolve gene_type column
    if "gene_type_c" in df.columns:
        df["gene_type"] = df["gene_type"].fillna(df["gene_type_c"])
        df.drop(columns=["gene_type_c"], inplace=True)
    if "source_dataset_c" in df.columns:
        df.drop(columns=["source_dataset_c"], inplace=True)

    df = df[df["split"] == args.split].copy()
    df = df[df["parsed_label"] != "UNPARSEABLE"].copy()
    df["correct"] = df.apply(is_correct, axis=1)
    df["norm_label"] = df.apply(lambda r: normalize_label(r["parsed_label"], r["format_type"]), axis=1)

    print(f"Rows (split={args.split}, parseable): {len(df)}")

    # ── Per-gene-type accuracy + FIR ──
    # FIR per category: facts where correctness differs across formats
    by_fact = defaultdict(dict)
    for _, row in df.iterrows():
        by_fact[row["fact_id"]][row["format_type"]] = {
            "correct": row["correct"],
            "gene_type": row.get("gene_type", "unknown"),
        }

    # Which facts are unstable, by gene_type
    unstable_by_type = defaultdict(set)
    total_facts_by_type = defaultdict(set)
    for fid, fmts in by_fact.items():
        if not fmts:
            continue
        gt = list(fmts.values())[0]["gene_type"]
        total_facts_by_type[gt].add(fid)
        correctness = [v["correct"] for v in fmts.values()]
        if len(fmts) >= 2 and len(set(correctness)) > 1:
            unstable_by_type[gt].add(fid)

    print(f"\n{'gene_type':<25} {'n_prompts':>10} {'accuracy':>10} {'FIR':>8} {'n_facts':>8}")
    print("─" * 68)

    category_records = {}
    for gt in GENE_TYPE_ORDER:
        sub = df[df["gene_type"] == gt]
        if len(sub) == 0:
            continue
        n = len(sub)
        acc = sub["correct"].mean()
        n_facts = len(total_facts_by_type.get(gt, set()))
        n_unstable = len(unstable_by_type.get(gt, set()))
        fir = n_unstable / n_facts if n_facts > 0 else 0.0
        print(f"{gt:<25} {n:>10} {acc:>9.1%} {fir:>7.1%} {n_facts:>8}")
        category_records[gt] = {
            "n_prompts": n,
            "n_facts": n_facts,
            "accuracy": round(float(acc), 4),
            "fir": round(fir, 4),
            "n_unstable_facts": n_unstable,
        }

    # Any gene_types not in the expected order
    for gt in sorted(df["gene_type"].dropna().unique()):
        if gt not in GENE_TYPE_ORDER:
            sub = df[df["gene_type"] == gt]
            n = len(sub)
            acc = sub["correct"].mean()
            n_facts = len(total_facts_by_type.get(gt, set()))
            n_unstable = len(unstable_by_type.get(gt, set()))
            fir = n_unstable / n_facts if n_facts > 0 else 0.0
            print(f"{gt:<25} {n:>10} {acc:>9.1%} {fir:>7.1%} {n_facts:>8}")
            category_records[gt] = {
                "n_prompts": n, "n_facts": n_facts,
                "accuracy": round(float(acc), 4), "fir": round(fir, 4),
                "n_unstable_facts": n_unstable,
            }

    # ── Hard-negative hallucination cases ──
    print(f"\nHard-negative hallucination cases (predicted SUPPORTED, gold NOT_SUPPORTED):")
    print(f"  (should all be NOT_SUPPORTED — any SUPPORTED is a false positive)")

    hn_df = df[df["gene_type"] == "hard_negative"].copy()
    hn_fp = hn_df[hn_df["norm_label"] == "SUPPORTED"]

    hallucination_cases = []
    if len(hn_fp) == 0:
        print("  None — model correctly avoided SUPPORTED for all hard-negative genes.")
    else:
        print(f"\n  {'gene':<12} {'format':<10} {'raw_output_snippet'}")
        print("  " + "─" * 70)
        for _, row in hn_fp.iterrows():
            raw = str(row.get("raw_output", "")).replace("\n", " ")[:120]
            print(f"  {row['gene']:<12} {row['format_type']:<10} {raw}")
            hallucination_cases.append({
                "id": row["id"],
                "gene": row["gene"],
                "format_type": row["format_type"],
                "parsed_label": row["parsed_label"],
                "raw_output_snippet": raw,
            })

    # ── Save outputs ──
    out_dir = args.outputs.parent
    json_out = {
        "split": args.split,
        "per_gene_type": category_records,
        "hard_negative_hallucinations": hallucination_cases,
    }
    json_path = out_dir / "gene_category_breakdown.json"
    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2)

    md_path = out_dir / "gene_category_breakdown.md"
    with open(md_path, "w") as md:
        md.write("# Gene Category Breakdown\n\n")
        md.write(f"**Split:** {args.split}  \n\n")

        md.write("## Per-Gene-Type Accuracy and Format Instability Rate\n\n")
        md.write("| Gene Type | Prompts | Facts | Accuracy | FIR |\n")
        md.write("|---|---|---|---|---|\n")
        for gt, rec in category_records.items():
            md.write(f"| {gt} | {rec['n_prompts']} | {rec['n_facts']} "
                     f"| {rec['accuracy']*100:.1f}% | {rec['fir']*100:.1f}% |\n")

        md.write("\n## Hard-Negative Hallucinations\n\n")
        md.write("Rows where the model predicted `SUPPORTED` for housekeeping genes "
                 "(gold = `NOT_SUPPORTED`).\n\n")
        if hallucination_cases:
            md.write("| Gene | Format | Parsed | Raw Output Snippet |\n")
            md.write("|---|---|---|---|\n")
            for h in hallucination_cases:
                snippet = h["raw_output_snippet"].replace("|", "\\|")
                md.write(f"| {h['gene']} | {h['format_type']} | `{h['parsed_label']}` | {snippet} |\n")
        else:
            md.write("_None — model correctly returned NOT_SUPPORTED for all hard-negative genes._\n")

    print(f"\n[Done] → {json_path}, {md_path}")


if __name__ == "__main__":
    main()

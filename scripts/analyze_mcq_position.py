"""
BioReasonCheck-FI · analyze_mcq_position.py
MCQ position bias: accuracy by correct-option position, model letter selection
distribution, and chi-square test for uniform selection.
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent

try:
    from scipy.stats import chisquare as _chisquare
    _SCIPY = True
except ImportError:
    _SCIPY = False


def extract_chosen_letter(raw_output: str) -> str:
    """Extract which letter (A/B/C/D) the model selected from the last 80 chars."""
    if not raw_output:
        return "UNKNOWN"
    tail = raw_output[-80:].upper()
    matches = re.findall(r"(?<![A-Z])([A-D])(?![A-Z])", tail)
    if not matches:
        # Broaden to full output
        matches = re.findall(r"(?<![A-Z])([A-D])(?![A-Z])", raw_output.upper())
    if not matches:
        return "UNKNOWN"
    unique = set(matches)
    if len(unique) == 1:
        return unique.pop()
    return "AMBIGUOUS"


def is_correct(row: pd.Series) -> bool:
    parsed = row["parsed_label"]
    if parsed == "UNPARSEABLE":
        return False
    return parsed == row["gold_label"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path,
                        default=ROOT / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--claims", type=Path,
                        default=ROOT / "data" / "processed" / "benchmark_claims.csv")
    args = parser.parse_args()

    rows = []
    with open(args.outputs, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)

    claims = pd.read_csv(args.claims)[["id", "correct_option"]]
    df = df.merge(claims, on="id", how="left", suffixes=("", "_c"))
    if "correct_option_c" in df.columns:
        df["correct_option"] = df["correct_option"].fillna(df["correct_option_c"])
        df.drop(columns=["correct_option_c"], inplace=True)

    # Filter to MCQ, test split, parseable
    df = df[(df["format_type"] == "mcq") & (df["split"] == "test")].copy()
    df = df[df["parsed_label"] != "UNPARSEABLE"].copy()
    df["correct"] = df.apply(is_correct, axis=1)
    df["chosen_letter"] = df["raw_output"].apply(extract_chosen_letter)

    print(f"MCQ test rows (parseable): {len(df)}")

    # ── A) Accuracy by correct_option position ──
    print(f"\nA) Accuracy by correct-option position:")
    print(f"  {'position':>10} {'n':>6} {'accuracy':>10}")
    print(f"  {'─'*30}")

    position_records = {}
    for pos in ["A", "B", "C", "D"]:
        sub = df[df["correct_option"].str.upper() == pos]
        n = len(sub)
        if n == 0:
            acc = None
            print(f"  {pos:>10} {n:>6} {'—':>10}")
        else:
            acc = sub["correct"].mean()
            print(f"  {pos:>10} {n:>6} {acc:>9.1%}")
        position_records[pos] = {"n": n, "accuracy": round(float(acc), 4) if acc is not None else None}

    # ── B) Model letter selection distribution ──
    print(f"\nB) Model letter selection distribution:")
    sel_counts = df["chosen_letter"].value_counts().to_dict()
    total = len(df)
    print(f"  {'letter':>8} {'count':>8} {'percent':>10}")
    print(f"  {'─'*30}")
    selection_records = {}
    for letter in ["A", "B", "C", "D"]:
        cnt = sel_counts.get(letter, 0)
        pct = cnt / total * 100 if total > 0 else 0.0
        print(f"  {letter:>8} {cnt:>8} {pct:>9.1f}%")
        selection_records[letter] = {"count": cnt, "pct": round(pct, 1)}
    # Report unknowns
    for letter in ["UNKNOWN", "AMBIGUOUS"]:
        cnt = sel_counts.get(letter, 0)
        if cnt > 0:
            print(f"  {letter:>8} {cnt:>8} (excluded from bias test)")
    selection_records["UNKNOWN"] = sel_counts.get("UNKNOWN", 0)
    selection_records["AMBIGUOUS"] = sel_counts.get("AMBIGUOUS", 0)

    # ── C) Position bias chi-square ──
    print(f"\nC) Position bias test (chi-square vs uniform 25% each):")
    abcd_counts = [sel_counts.get(l, 0) for l in ["A", "B", "C", "D"]]
    valid_total = sum(abcd_counts)
    expected = [valid_total / 4] * 4

    chi2_stat = None
    p_val = None
    if valid_total >= 4:
        if _SCIPY:
            result = _chisquare(abcd_counts, f_exp=expected)
            chi2_stat = result.statistic
            p_val = result.pvalue
            print(f"  chi2={chi2_stat:.3f}, p={p_val:.4f}")
        else:
            # Manual chi-square
            chi2_stat = sum((o - e) ** 2 / e for o, e in zip(abcd_counts, expected) if e > 0)
            print(f"  chi2={chi2_stat:.3f} (scipy not available — no p-value)")

        sig = p_val is not None and p_val < 0.05
        if sig:
            dominant = ["A", "B", "C", "D"][abcd_counts.index(max(abcd_counts))]
            print(f"  → Model SHOWS significant letter preference (p<0.05). "
                  f"Most selected: {dominant} ({max(abcd_counts)}/{valid_total})")
        else:
            print(f"  → Model does NOT show significant letter preference at p<0.05.")
    else:
        print(f"  Too few MCQ rows ({valid_total}) to test.")

    # ── Save outputs ──
    out_dir = args.outputs.parent
    json_out = {
        "n_mcq_test": len(df),
        "accuracy_by_position": position_records,
        "model_selection_distribution": selection_records,
        "position_bias": {
            "chi2": round(chi2_stat, 4) if chi2_stat is not None else None,
            "p": round(p_val, 4) if p_val is not None else None,
            "significant": bool(p_val < 0.05) if p_val is not None else None,
        },
    }
    json_path = out_dir / "mcq_position_bias.json"
    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2)

    md_path = out_dir / "mcq_position_bias.md"
    with open(md_path, "w") as md:
        md.write("# MCQ Position Bias Analysis\n\n")

        md.write("## A) Accuracy by Correct-Option Position\n\n")
        md.write("| Position | N | Accuracy |\n|---|---|---|\n")
        for pos, rec in position_records.items():
            acc_str = f"{rec['accuracy']*100:.1f}%" if rec["accuracy"] is not None else "—"
            md.write(f"| {pos} | {rec['n']} | {acc_str} |\n")

        md.write("\n## B) Model Letter Selection Distribution\n\n")
        md.write("| Letter | Count | % |\n|---|---|---|\n")
        for letter in ["A", "B", "C", "D"]:
            rec = selection_records.get(letter, {"count": 0, "pct": 0.0})
            md.write(f"| {letter} | {rec['count']} | {rec['pct']}% |\n")

        md.write("\n## C) Position Bias Chi-Square Test\n\n")
        pb = json_out["position_bias"]
        if pb["chi2"] is not None:
            md.write(f"**χ²** = {pb['chi2']:.3f}")
            if pb["p"] is not None:
                md.write(f", **p** = {pb['p']:.4f}")
            md.write("  \n")
            if pb["significant"]:
                md.write("→ **Statistically significant** letter preference detected (p < 0.05).\n")
            else:
                md.write("→ No statistically significant letter preference at p < 0.05.\n")
        else:
            md.write("_Insufficient data for chi-square test._\n")

    print(f"\n[Done] → {json_path}, {md_path}")


if __name__ == "__main__":
    main()

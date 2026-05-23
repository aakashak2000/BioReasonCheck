"""
BioReasonCheck-FI · evaluate.py
Computes accuracy, macro F1, balanced accuracy, confusion matrix,
per-format metrics, format instability rate, Wilson CI, McNemar test,
and per-gene-type accuracy breakdown.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)

try:
    from scipy.stats import chi2 as _chi2_dist
    _SCIPY = True
except ImportError:
    _SCIPY = False

ROOT = Path(__file__).parent.parent
LABELS_3 = ["SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]

HARD_NEGATIVE_GENES = {
    "GAPDH","ACTB","TUBB","LDHA","PKM","ENO1","TPI1",
    "ALDOA","PGK1","PGAM1","FASN","ACACA","ACLY","SUCLA2","SDHA",
}
FAKE_TRAP_GENES = {"AGEX1","LNVT3","SNRP9X","FOXQ7L","TERT2B"}


# ─────────────────────────── helpers ─────────────────────────────────────────

def is_correct(row: pd.Series) -> bool:
    fmt = row["format_type"]
    if fmt == "binary":
        return row["parsed_label"] == row["correct_answer"]
    return row["parsed_label"] == row["gold_label"]


def format_confusion_matrix(cm: np.ndarray, labels: list) -> str:
    col_w = 22
    lines = [f"\n{'Actual ↓':<{col_w}}" + "".join(f"{l:>{col_w}}" for l in labels)]
    for i, label in enumerate(labels):
        lines.append(f"{label:<{col_w}}" + "".join(f"{cm[i,j]:>{col_w}}" for j in range(len(labels))))
    return "\n".join(lines)


def wilson_ci(k: int, n: int) -> tuple:
    """Wilson score 95% CI for proportion k/n."""
    if n < 2:
        return None, None
    p_tilde = (k + 1.92) / (n + 3.84)
    margin = (1.96 / (n + 3.84)) * math.sqrt(k * (n - k) / n + 0.96)
    lo = max(0.0, p_tilde - margin)
    hi = min(1.0, p_tilde + margin)
    return lo, hi


def mcnemar_test(b: int, c: int) -> tuple:
    """McNemar test with Yates continuity correction. Returns (chi2, p)."""
    total = b + c
    if total == 0:
        return None, None
    chi2_stat = (abs(b - c) - 1) ** 2 / total
    if _SCIPY:
        p = _chi2_dist.sf(chi2_stat, df=1)
    else:
        # Exact binomial fallback
        smaller = min(b, c)
        p = 2 * sum(math.comb(total, i) * 0.5 ** total for i in range(smaller + 1))
        p = min(p, 1.0)
    return chi2_stat, p


def infer_gene_type(row: pd.Series) -> str:
    src = str(row.get("source_dataset", "")).strip()
    gold = str(row.get("gold_label", "")).strip()
    gene = str(row.get("gene", "")).strip().upper()
    if src == "CellAge":
        return "cellage"
    if src == "OpenGenes":
        if gold == "SUPPORTED":
            return "og_lifespan_extending"
        if gold == "INSUFFICIENT_EVIDENCE":
            return "og_mixed"
    if gold == "NOT_SUPPORTED":
        if gene in HARD_NEGATIVE_GENES:
            return "hard_negative"
        return "fake_trap"
    return "unknown"


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

    if not args.outputs.exists():
        print(f"[WARN] file not found: {args.outputs}")
        return
    if not args.claims.exists():
        print(f"[WARN] file not found: {args.claims}")
        return

    # ── Load data ──
    claims = pd.read_csv(args.claims)
    outputs_rows = []
    with open(args.outputs, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                outputs_rows.append(json.loads(line))
    outputs = pd.DataFrame(outputs_rows)

    # Merge — bring in correct_answer, split, gene_type, source_dataset, claim_text
    merge_cols = [c for c in ["id","correct_answer","correct_option","split",
                               "gene_type","source_dataset","claim_text","prompt"]
                  if c in claims.columns]
    df = outputs.merge(claims[merge_cols], on="id", how="left", suffixes=("", "_claims"))
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

    # ── Overall 3-class metrics (ternary subset) ──
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
        else:
            f1_fmt = fmt_acc
        print(f"  {fmt:8s}: accuracy={fmt_acc:.4f}  f1={f1_fmt:.4f}  n={len(sub)}")
        fmt_metrics[fmt] = {"accuracy": round(fmt_acc, 4), "f1": round(f1_fmt, 4), "n": len(sub)}
    metrics["per_format"] = fmt_metrics

    # ── Format Instability Rate ──
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
            fmt_correct[row["format_type"]] = bool(row["correct"])
        stable = len(set(fmt_correct.values())) == 1
        if not stable:
            unstable_count += 1
        instability_table.append({
            "fact_id": fact_id,
            "gene": group["gene"].iloc[0],
            "binary_ok": fmt_correct.get("binary"),
            "ternary_ok": fmt_correct.get("ternary"),
            "mcq_ok": fmt_correct.get("mcq"),
            "stable": stable,
        })

    fir = unstable_count / facts_with_2plus if facts_with_2plus > 0 else 0.0
    print(f"  Unstable facts:         {unstable_count} / {facts_with_2plus}")
    print(f"  FORMAT INSTABILITY RATE: {fir:.4f} ({fir*100:.1f}%)")

    def fmt_bool(v):
        if v is None: return "  -"
        return "  ✓" if v else "  ✗"

    print(f"\n  {'fact_id':<8} {'gene':<12} {'binary':>7} {'ternary':>8} {'mcq':>5} {'stable':>7}")
    print("  " + "-" * 52)
    for r in sorted(instability_table, key=lambda x: x["fact_id"]):
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
        majority_f1 = f1_score(df_ternary["gold_label"].tolist(),
                                [most_common] * len(df_ternary),
                                labels=LABELS_3, average="macro", zero_division=0)
        random_acc = 1 / 3
        print(f"  Majority class ({most_common}): accuracy = {majority_acc:.4f}")
        print(f"  Random uniform:                accuracy = {random_acc:.4f}")
        metrics["baselines"] = {
            "majority_class": most_common,
            "majority_accuracy": round(majority_acc, 4),
            "majority_f1": round(majority_f1, 4),
            "random_accuracy": round(random_acc, 4),
            "random_f1": round(1/3, 4),
        }

    metrics["unparseable"] = {"count": int(unp), "total": len(df)}

    # ═══════════════════════════════════════════════════════════
    # TASK 1A — Wilson score 95% CI on FIR
    # ═══════════════════════════════════════════════════════════
    print(f"\n── Statistical Tests ──")
    stat_tests = {}

    k_fir = unstable_count
    n_fir = facts_with_2plus
    if n_fir < 2:
        print("  Wilson CI: not enough paired data")
        stat_tests["wilson_note"] = "not enough paired data"
    else:
        lo, hi = wilson_ci(k_fir, n_fir)
        fir_pct = k_fir / n_fir if n_fir > 0 else 0.0
        print(f"  FIR = {k_fir}/{n_fir} = {fir_pct:.1%} [95% CI: {lo:.1%}–{hi:.1%}]")
        stat_tests["wilson_ci_lo"] = round(lo, 4)
        stat_tests["wilson_ci_hi"] = round(hi, 4)
        stat_tests["wilson_k"] = k_fir
        stat_tests["wilson_n"] = n_fir

    # ═══════════════════════════════════════════════════════════
    # TASK 1B — McNemar's test: binary vs MCQ on matched test facts
    # ═══════════════════════════════════════════════════════════
    df_binary = df_valid[df_valid["format_type"] == "binary"].set_index("fact_id")
    df_mcq    = df_valid[df_valid["format_type"] == "mcq"].set_index("fact_id")
    common_facts = set(df_binary.index) & set(df_mcq.index)

    b_count, c_count = 0, 0
    for fid in common_facts:
        b_ok = bool(df_binary.loc[fid, "correct"])
        m_ok = bool(df_mcq.loc[fid, "correct"])
        if b_ok and not m_ok:
            b_count += 1
        elif not b_ok and m_ok:
            c_count += 1

    if b_count + c_count == 0:
        print("  McNemar test (binary vs MCQ): not enough paired data")
        stat_tests["mcnemar_note"] = "not enough paired data"
    else:
        chi2_stat, p_val = mcnemar_test(b_count, c_count)
        print(f"  McNemar test (binary vs MCQ): b={b_count}, c={c_count}, "
              f"chi2={chi2_stat:.3f}, p={p_val:.4f}")
        stat_tests["mcnemar_b"] = b_count
        stat_tests["mcnemar_c"] = c_count
        stat_tests["mcnemar_chi2"] = round(chi2_stat, 4)
        stat_tests["mcnemar_p"] = round(p_val, 4)

    metrics["statistical_tests"] = stat_tests

    # ═══════════════════════════════════════════════════════════
    # TASK 1C — Per-gene-type accuracy breakdown
    # ═══════════════════════════════════════════════════════════
    print(f"\n── Per-gene-type accuracy ──")
    if "gene_type" not in df_valid.columns:
        # Infer from source_dataset + gold_label
        print("  [WARN] gene_type column missing — inferring from source_dataset + gold_label")
        merge_cols2 = [c for c in ["id","source_dataset","gene_type"] if c in claims.columns]
        df_valid = df_valid.merge(claims[merge_cols2], on="id", how="left",
                                  suffixes=("","_c"))
        if "gene_type" not in df_valid.columns:
            df_valid["gene_type"] = df_valid.apply(infer_gene_type, axis=1)

    if "gene_type" not in df_valid.columns or df_valid["gene_type"].isna().all():
        print("  [WARN] could not resolve gene_type — not enough paired data")
        metrics["per_gene_type"] = "not enough paired data"
    else:
        df_valid["gene_type"] = df_valid["gene_type"].fillna("unknown")
        pgt = {}
        print(f"  {'gene_type':<28} {'n':>5} {'accuracy':>10}")
        print("  " + "-" * 46)
        for gt, grp in df_valid.groupby("gene_type"):
            acc = grp["correct"].mean()
            pgt[gt] = {"n": len(grp), "accuracy": round(float(acc), 4)}
            print(f"  {gt:<28} {len(grp):>5} {acc:>10.4f}")
        metrics["per_gene_type"] = pgt

    # ── Save metrics.json ──
    out_dir = ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # ── Build metrics.md ──
    md_lines = [
        "# BioReasonCheck-FI · Evaluation Report",
        f"\n**Split:** {args.split}  |  **Total rows:** {len(df)}  |  **UNPARSEABLE:** {unp}",
        "\n## Headline Metric: Format Instability Rate",
        "\n| Metric | Value |",
        "| --- | --- |",
        f"| FORMAT INSTABILITY RATE | **{fir:.4f}** ({fir*100:.1f}%) |",
        f"| Unstable facts | {unstable_count} / {facts_with_2plus} |",
    ]
    if "wilson_ci_lo" in stat_tests:
        md_lines.append(
            f"| Wilson 95% CI | [{stat_tests['wilson_ci_lo']:.1%}–{stat_tests['wilson_ci_hi']:.1%}] |"
        )
    if "overall" in metrics:
        o = metrics["overall"]
        md_lines += [
            "\n## Overall Metrics (ternary, 3-class)",
            "\n| Metric | Value |",
            "| --- | --- |",
            f"| Accuracy | {o['accuracy']} |",
            f"| Macro F1 | {o['macro_f1']} |",
            f"| Balanced Accuracy | {o['balanced_accuracy']} |",
        ]
    if "per_format" in metrics:
        md_lines += ["\n## Per-Format Metrics",
                     "\n| Format | Accuracy | F1 | N |",
                     "| --- | --- | --- | --- |"]
        for fmt, v in metrics["per_format"].items():
            md_lines.append(f"| {fmt} | {v['accuracy']} | {v['f1']} | {v['n']} |")
    if "baselines" in metrics:
        b = metrics["baselines"]
        md_lines += [
            "\n## Baselines",
            "\n| Baseline | Accuracy | Macro F1 |",
            "| --- | --- | --- |",
            f"| Majority class ({b['majority_class']}) | {b['majority_accuracy']} | {b['majority_f1']} |",
            f"| Random (uniform 3-class) | {b['random_accuracy']} | {b['random_f1']} |",
        ]
    # Statistical tests table
    md_lines += ["\n## Statistical Tests", "\n| Test | Result |", "| --- | --- |"]
    if "wilson_ci_lo" in stat_tests:
        md_lines.append(
            f"| Wilson 95% CI on FIR | [{stat_tests['wilson_ci_lo']:.1%}–{stat_tests['wilson_ci_hi']:.1%}] (k={stat_tests['wilson_k']}, n={stat_tests['wilson_n']}) |"
        )
    if "mcnemar_chi2" in stat_tests:
        md_lines.append(
            f"| McNemar (binary vs MCQ) | b={stat_tests['mcnemar_b']}, c={stat_tests['mcnemar_c']}, χ²={stat_tests['mcnemar_chi2']:.3f}, p={stat_tests['mcnemar_p']:.4f} |"
        )
    # Per-gene-type table
    if isinstance(metrics.get("per_gene_type"), dict):
        md_lines += ["\n## Per-Gene-Type Accuracy",
                     "\n| Gene Type | N | Accuracy |",
                     "| --- | --- | --- |"]
        for gt, v in metrics["per_gene_type"].items():
            md_lines.append(f"| {gt} | {v['n']} | {v['accuracy']} |")

    with open(out_dir / "metrics.md", "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\n[Done] Saved → {out_dir / 'metrics.json'}, {out_dir / 'metrics.md'}")


if __name__ == "__main__":
    main()

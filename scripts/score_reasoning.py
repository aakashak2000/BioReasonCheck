"""
BioReasonCheck-FI · score_reasoning.py
Scores L-LLM reasoning traces to predict when the model gets answers wrong.

Signals:
  1. hallucination_score  — fraction of gene-like tokens in trace NOT in valid_genes
  2. consistency_score    — semantic alignment between trace conclusion and final answer
  3. composite_score      — weighted combination (lower = worse reasoning)

Reports Pearson r between (1 - composite_score) and model error.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

ROOT = Path(__file__).parent.parent

# Tokens to exclude from gene-symbol detection in reasoning traces.
# Includes task labels, MCQ option letters, common English uppercase words,
# and biology terms that are not gene symbols.
EXCLUDED_TOKENS = {
    # Task answer labels
    "SUPPORTED", "NOT", "INSUFFICIENT", "EVIDENCE", "NOT_SUPPORTED",
    "INSUFFICIENT_EVIDENCE",
    "YES", "NO", "UNPARSEABLE",
    # MCQ option letters
    "A", "B", "C", "D",
    # Common English words that surface as uppercase in reasoning
    "THE", "IS", "IN", "AT", "BY", "OR", "AND", "TO", "OF", "FOR",
    "WITH", "FROM", "AS", "AN", "ON", "BE", "HAS", "ARE", "CAN",
    "MAY", "DO", "SO", "IF", "IT", "ITS", "ANY", "ALL", "ONE", "TWO",
    "BUT", "THAT", "THIS", "WAS", "HAD", "HIM", "HIS", "HAVE", "BEEN",
    "WILL", "WOULD", "COULD", "SHOULD", "MORE", "ALSO", "SUCH", "BOTH",
    "EACH", "THAN", "THEN", "WHEN", "WELL", "JUST", "ONLY", "VERY",
    "MOST", "SOME", "MANY", "MUCH", "EVEN", "ALSO", "THUS", "HENCE",
    "SINCE", "WHILE", "AFTER", "BASED", "GIVEN", "USING", "DOES",
    "USED", "NEED", "MUST", "INTO", "OVER", "UPON", "ABOUT", "ABOVE",
    "THEIR", "THESE", "THOSE", "WHICH", "THERE", "FIRST", "SECOND",
    "CLAIM", "TRUE", "FALSE", "CORRECT", "WRONG", "ANSWER", "LABEL",
    # Biology / domain terms that look like gene symbols
    "DNA", "RNA", "PCR", "AGE", "GENE", "GENES", "AGING", "CELL",
    "CELLS", "HUMAN", "MOUSE", "MICE", "PROTEIN", "PROTEINS", "PATHWAY",
    "CANCER", "NULL", "NONE", "NAN", "NA", "DB", "MCQ", "LLM", "AI",
    "STATED", "DATABASE", "LISTED", "EVIDENCE", "CELLULAR", "SENESCENCE",
    "MAMMALIAN", "LIFESPAN", "CONFIDENCE", "OPENGENES", "CELLAGE",
    "LONGEVITY", "BIOMARKER", "ANNOTATION", "METABOLIC", "GENERAL",
    "CONTAINS", "CONTAIN", "ENTRY", "ACTIVITY", "EXTENDS", "REDUCES",
    "ASSOCIATED", "ASSOCIATION", "EXPRESSION", "FUNCTION", "COMPLEX",
    "KNOWN", "WELL", "BIOLOGY", "BIOLOGICAL", "AGING", "RELATED",
    "VARIANT", "VARIANTS", "STUDY", "STUDIES", "HALLMARK", "HALLMARKS",
    "STRESS", "REPAIR", "CYCLE", "ARREST", "APOPTOSIS", "AUTOPHAGY",
    "IGF", "MTOR", "ROS", "CG", "CPG", "CPGS",
}

# Patterns that suggest the trace CONCLUDES supported / not-supported
_SUPPORT_PATTERNS = [
    r"\bsupports?\b", r"\bconfirm(s|ed)?\b", r"\bverif(y|ied|ies)\b",
    r"\bcorrect\b", r"\btrue\b", r"\byes\b", r"\bdoes exist\b",
    r"\bis listed\b", r"\bfound in\b", r"\bpresent in\b",
    r"\bincluded in\b", r"\bpart of\b", r"\bbelongs? to\b",
]
_REJECT_PATTERNS = [
    r"\bnot supported\b", r"\bnot found\b", r"\bnot listed\b",
    r"\bnot in\b", r"\bdoes not exist\b", r"\bno entry\b",
    r"\bincorrect\b", r"\bfalse\b", r"\binvalid\b",
    r"\bno evidence\b", r"\bno support\b", r"\bunknown\b",
    r"\bno record\b", r"\bnot present\b",
]
_UNCERTAIN_PATTERNS = [
    r"\binsufficient\b", r"\buncertain\b", r"\bunclear\b",
    r"\blimited evidence\b", r"\bmixed\b", r"\bcontroversial\b",
    r"\bweak evidence\b", r"\bpossibly\b", r"\bmay or may not\b",
]


def load_valid_genes(path: Path) -> set:
    df = pd.read_csv(path)
    return set(df["gene"].str.upper().dropna())


def extract_gene_candidates(text: str) -> list[str]:
    """Extract 2–10 char uppercase tokens (possible gene symbols)."""
    tokens = re.findall(r"\b([A-Z][A-Z0-9]{1,9})\b", text)
    return [t for t in tokens if t not in EXCLUDED_TOKENS]


def hallucination_score(trace: str, valid_genes: set) -> float:
    """
    Fraction of gene-like tokens in trace that are NOT in valid_genes.
    0 = all mentions are valid genes (no hallucination).
    1 = all mentions are invalid (full hallucination).
    Returns 0.5 if no gene-like tokens found (neutral).
    """
    candidates = extract_gene_candidates(trace)
    if not candidates:
        return 0.5
    invalid = sum(1 for g in candidates if g not in valid_genes)
    return invalid / len(candidates)


def consistency_score(trace: str, parsed_label: str) -> float:
    """
    How well does the reasoning trace's implied conclusion match the final answer?
    Returns 1.0 (fully consistent) → 0.0 (fully inconsistent).
    """
    if not trace or parsed_label == "UNPARSEABLE":
        return 0.5  # neutral

    trace_lower = trace.lower()
    support_hits = sum(bool(re.search(p, trace_lower)) for p in _SUPPORT_PATTERNS)
    reject_hits = sum(bool(re.search(p, trace_lower)) for p in _REJECT_PATTERNS)
    uncertain_hits = sum(bool(re.search(p, trace_lower)) for p in _UNCERTAIN_PATTERNS)

    # Infer trace conclusion
    if support_hits > reject_hits and support_hits > uncertain_hits:
        trace_conclusion = "SUPPORTED"
    elif reject_hits > support_hits and reject_hits > uncertain_hits:
        trace_conclusion = "NOT_SUPPORTED"
    elif uncertain_hits >= support_hits and uncertain_hits >= reject_hits:
        trace_conclusion = "INSUFFICIENT_EVIDENCE"
    else:
        return 0.5  # ambiguous

    # Normalize parsed_label to 3-class
    label_upper = parsed_label.upper()
    if label_upper in ("YES",):
        label_upper = "SUPPORTED"
    elif label_upper in ("NO",):
        label_upper = "NOT_SUPPORTED"

    return 1.0 if trace_conclusion == label_upper else 0.0


def composite_score(hall: float, cons: float,
                    w_hall: float = 0.4, w_cons: float = 0.6) -> float:
    """
    Higher composite = better reasoning quality.
    hall: 0=no hallucination (good), 1=all hallucination (bad) → invert
    cons: 1=consistent (good), 0=inconsistent (bad)
    """
    return w_hall * (1.0 - hall) + w_cons * cons


def is_correct(row: pd.Series) -> bool:
    fmt = row["format_type"]
    if fmt == "binary":
        return row["parsed_label"] == row["correct_answer"]
    return row["parsed_label"] == row["gold_label"]


def main():
    parser = argparse.ArgumentParser(description="Score L-LLM reasoning traces")
    parser.add_argument("--outputs", type=Path,
                        default=ROOT / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--valid-genes", type=Path,
                        default=ROOT / "data" / "processed" / "valid_genes.csv")
    parser.add_argument("--claims", type=Path,
                        default=ROOT / "data" / "processed" / "benchmark_claims.csv")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "outputs" / "reasoning_scores.jsonl")
    args = parser.parse_args()

    valid_genes = load_valid_genes(args.valid_genes)
    print(f"Loaded {len(valid_genes)} valid gene symbols")

    claims = pd.read_csv(args.claims)[["id", "correct_answer", "split"]]

    rows = []
    with open(args.outputs, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df = df.merge(claims, on="id", how="left", suffixes=("", "_c"))
    for col in ("correct_answer", "split"):
        if f"{col}_c" in df.columns:
            df[col] = df[col].fillna(df[f"{col}_c"])
            df.drop(columns=[f"{col}_c"], inplace=True)

    # ── Compute scores ──
    scored = []
    for _, row in df.iterrows():
        trace = row.get("thinking_trace", "") or ""
        parsed = row.get("parsed_label", "UNPARSEABLE")

        hall = hallucination_score(trace, valid_genes)
        cons = consistency_score(trace, parsed)
        comp = composite_score(hall, cons)

        correct = is_correct(row) if parsed != "UNPARSEABLE" else None

        gene_mentions = extract_gene_candidates(trace)
        invalid_mentions = [g for g in gene_mentions if g not in valid_genes]

        record = {
            "id": row["id"],
            "fact_id": row["fact_id"],
            "gene": row["gene"],
            "format_type": row["format_type"],
            "split": row.get("split", ""),
            "gold_label": row["gold_label"],
            "parsed_label": parsed,
            "correct": correct,
            "hallucination_score": round(hall, 4),
            "consistency_score": round(cons, 4),
            "composite_score": round(comp, 4),
            "gene_mentions": gene_mentions[:20],
            "invalid_gene_mentions": invalid_mentions[:10],
            "trace_length": len(trace),
        }
        scored.append(record)

    scored_df = pd.DataFrame(scored)

    # ── Save scored outputs ──
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in scored:
            f.write(json.dumps(r) + "\n")

    # ── Correlation analysis ──
    print(f"\n{'='*60}")
    print("Reasoning Trace Score Analysis")
    print(f"{'='*60}")

    valid_df = scored_df[scored_df["parsed_label"] != "UNPARSEABLE"].copy()
    valid_df["error"] = (~valid_df["correct"]).astype(float)

    print(f"\nTotal rows: {len(scored_df)}  |  Parseable: {len(valid_df)}")
    print(f"\nScore summary (all rows):")
    print(f"  hallucination_score  mean={scored_df['hallucination_score'].mean():.3f}  "
          f"std={scored_df['hallucination_score'].std():.3f}")
    print(f"  consistency_score    mean={scored_df['consistency_score'].mean():.3f}  "
          f"std={scored_df['consistency_score'].std():.3f}")
    print(f"  composite_score      mean={scored_df['composite_score'].mean():.3f}  "
          f"std={scored_df['composite_score'].std():.3f}")

    if len(valid_df) >= 5:
        # Pearson r: does lower composite score predict model error?
        r_comp, p_comp = pearsonr(1 - valid_df["composite_score"], valid_df["error"])
        r_hall, p_hall = pearsonr(valid_df["hallucination_score"], valid_df["error"])
        r_cons, p_cons = pearsonr(1 - valid_df["consistency_score"], valid_df["error"])

        print(f"\n── Pearson r with model error (higher r = better predictor) ──")
        print(f"  1 - composite_score:     r={r_comp:+.4f}  p={p_comp:.4f}")
        print(f"  hallucination_score:     r={r_hall:+.4f}  p={p_hall:.4f}")
        print(f"  1 - consistency_score:   r={r_cons:+.4f}  p={p_cons:.4f}")

        # Threshold analysis: flag rows with composite_score < 0.5 as "predicted wrong"
        threshold = 0.5
        valid_df["predicted_wrong"] = valid_df["composite_score"] < threshold
        tp = ((valid_df["predicted_wrong"]) & (valid_df["error"] == 1)).sum()
        fp = ((valid_df["predicted_wrong"]) & (valid_df["error"] == 0)).sum()
        fn = ((~valid_df["predicted_wrong"]) & (valid_df["error"] == 1)).sum()
        tn = ((~valid_df["predicted_wrong"]) & (valid_df["error"] == 0)).sum()
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0

        print(f"\n── Threshold={threshold}: composite_score < threshold → predict error ──")
        print(f"  Precision: {prec:.4f}  Recall: {rec:.4f}  F1: {f1:.4f}")
        print(f"  TP={tp}  FP={fp}  FN={fn}  TN={tn}")

        summary = {
            "pearson_r_composite": round(r_comp, 4),
            "pearson_p_composite": round(p_comp, 4),
            "pearson_r_hallucination": round(r_hall, 4),
            "pearson_r_consistency": round(r_cons, 4),
            "threshold_precision": round(prec, 4),
            "threshold_recall": round(rec, 4),
            "threshold_f1": round(f1, 4),
        }
        with open(args.out.parent / "reasoning_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

    # ── Per-format breakdown ──
    print(f"\n── Per-format score breakdown ──")
    for fmt in ["binary", "ternary", "mcq"]:
        sub = valid_df[valid_df["format_type"] == fmt]
        if len(sub) == 0:
            continue
        acc = sub["correct"].mean()
        avg_comp = sub["composite_score"].mean()
        avg_hall = sub["hallucination_score"].mean()
        print(f"  {fmt:8s}: accuracy={acc:.3f}  "
              f"avg_composite={avg_comp:.3f}  avg_hallucination={avg_hall:.3f}  n={len(sub)}")

    # ── Top hallucinated genes ──
    all_invalid = []
    for r in scored:
        all_invalid.extend(r.get("invalid_gene_mentions", []))
    from collections import Counter
    top_hallucinated = Counter(all_invalid).most_common(10)
    if top_hallucinated:
        print(f"\n── Top hallucinated gene tokens (not in valid_genes) ──")
        for token, count in top_hallucinated:
            print(f"  {token}: {count}")

    print(f"\n[Done] Scored {len(scored)} rows → {args.out}")


if __name__ == "__main__":
    main()

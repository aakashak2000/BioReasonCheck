"""
BioReasonCheck · analyze_trace_errors.py
Trace error taxonomy: process-as-gene, consistency mismatch,
source misattribution, and fake-trap bleed.

Works on model_outputs.jsonl (raw_output) and optionally merges
thinking_trace from traces_ternary.jsonl for deeper analysis.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent

PROCESS_TERMS = [
    "SASP", "MTORC1", "MTOR", "AUTOPHAGY", "INFLAMMAGING",
    "NFKB", "NF-KB", "MITOPHAGY", "PROTEOSTASIS", "TELOMERE SHORTENING",
    "SENESCENCE", "APOPTOSIS", "OXIDATIVE STRESS", "EPIGENETIC DRIFT",
    "INSULIN SIGNALING", "IGF PATHWAY", "TOR PATHWAY", "SIRTUIN PATHWAY",
]

FAKE_TRAPS = ["AGEX1", "LNVT3", "SNRP9X", "FOXQ7L", "TERT2B"]

_POSITIVE_PHRASES = [
    r"\bsupports?\b", r"\bconfirm(s|ed)?\b", r"\bfound in\b",
    r"\bis listed\b", r"\bpresent in\b", r"\bbelongs? to\b", r"\byes\b",
]
_NEGATIVE_PHRASES = [
    r"\bnot supported\b", r"\bnot found\b", r"\bnot listed\b",
    r"\bdoes not exist\b", r"\bno entry\b", r"\bno evidence\b", r"\bno\b",
]


def normalize_label(label: str, fmt: str) -> str:
    if fmt == "binary":
        if label == "YES":
            return "SUPPORTED"
        if label == "NO":
            return "NOT_SUPPORTED"
    return label


def is_correct_row(row: pd.Series) -> bool:
    fmt = row["format_type"]
    parsed = row["parsed_label"]
    if parsed == "UNPARSEABLE":
        return False
    if fmt == "binary":
        return parsed == row["correct_answer"]
    return parsed == row["gold_label"]


def check_process_as_gene(text: str, gene: str) -> list[str]:
    """Return process terms found in text that are not the gene being queried."""
    gene_upper = gene.upper()
    text_upper = text.upper()
    found = []
    for term in PROCESS_TERMS:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, text_upper):
            # Not if the term IS the gene name
            if term != gene_upper:
                found.append(term)
    return found


def check_consistency_mismatch(text: str, norm_label: str) -> bool:
    """Simple consistency: positive phrase in output but label is NOT_SUPPORTED, or vice versa."""
    if not text or norm_label == "UNPARSEABLE":
        return False
    text_lower = text.lower()
    has_positive = any(re.search(p, text_lower) for p in _POSITIVE_PHRASES)
    has_negative = any(re.search(p, text_lower) for p in _NEGATIVE_PHRASES)
    if norm_label == "NOT_SUPPORTED" and has_positive and not has_negative:
        return True
    if norm_label == "SUPPORTED" and has_negative and not has_positive:
        return True
    return False


def check_source_misattribution(text: str, gene: str,
                                 cellage_genes: set, og_genes: set) -> bool:
    """Model mentions CellAge/OpenGenes but gene isn't in that DB."""
    text_upper = text.upper()
    gene_upper = gene.upper()
    mentions_cellage = bool(re.search(r"\bCELLAGE\b", text_upper))
    mentions_og = bool(re.search(r"\bOPENGENES\b", text_upper))
    if mentions_cellage and gene_upper not in cellage_genes:
        return True
    if mentions_og and gene_upper not in og_genes:
        return True
    return False


def check_fake_trap_bleed(text: str, gene: str) -> list[str]:
    """Fake-trap symbol in output for a non-trap gene."""
    gene_upper = gene.upper()
    if gene_upper in [ft.upper() for ft in FAKE_TRAPS]:
        return []  # skip trap rows themselves
    text_upper = text.upper()
    return [ft for ft in FAKE_TRAPS
            if re.search(r"\b" + re.escape(ft) + r"\b", text_upper)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path,
                        default=ROOT / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--cellage-ref", type=Path,
                        default=ROOT / "data" / "processed" / "cellage_ref.csv")
    parser.add_argument("--opengenes-ref", type=Path,
                        default=ROOT / "data" / "processed" / "opengenes_ref.csv")
    parser.add_argument("--traces", type=Path,
                        default=ROOT / "outputs" / "traces_ternary.jsonl",
                        help="Optional thinking traces to augment raw_output analysis")
    args = parser.parse_args()

    # Load reference gene sets
    cellage_genes = set(pd.read_csv(args.cellage_ref)["gene"].str.upper())
    og_genes = set(pd.read_csv(args.opengenes_ref)["gene"].str.upper())
    print(f"Loaded {len(cellage_genes)} CellAge genes, {len(og_genes)} OpenGenes genes")

    # Load thinking traces keyed by id
    trace_by_id = {}
    if args.traces.exists():
        with open(args.traces, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    trace_by_id[r["id"]] = r.get("thinking_trace", "") or ""
        print(f"Loaded {len(trace_by_id)} thinking traces from {args.traces.name}")

    # Load model outputs
    rows = []
    with open(args.outputs, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df = df[df["raw_output"].notna() & (df["raw_output"] != "")].copy()
    df = df[df["parsed_label"] != "UNPARSEABLE"].copy()
    df["norm_label"] = df.apply(lambda r: normalize_label(r["parsed_label"], r["format_type"]), axis=1)
    df["correct"] = df.apply(is_correct_row, axis=1)

    print(f"Rows with non-empty raw_output + parseable: {len(df)}")

    # ── Classify each row ──
    taxonomy = []
    process_instances = []

    for _, row in df.iterrows():
        raw = str(row["raw_output"]) or ""
        # Augment with thinking trace if available
        trace = trace_by_id.get(row["id"], "")
        full_text = (raw + " " + trace).strip()

        gene = str(row["gene"])
        norm_label = row["norm_label"]
        correct = row["correct"]

        # Flag 1: process_as_gene
        proc_terms = check_process_as_gene(full_text, gene)
        flag_proc = len(proc_terms) > 0

        # Flag 2: consistency_mismatch
        flag_cons = check_consistency_mismatch(full_text, norm_label)

        # Flag 3: source_misattribution
        flag_src = check_source_misattribution(full_text, gene, cellage_genes, og_genes)

        # Flag 4: fake_trap_bleed
        bleed_traps = check_fake_trap_bleed(full_text, gene)
        flag_bleed = len(bleed_traps) > 0

        rec = {
            "id": row["id"],
            "fact_id": row["fact_id"],
            "gene": gene,
            "format_type": row["format_type"],
            "gold_label": row["gold_label"],
            "parsed_label": row["parsed_label"],
            "correct": correct,
            "flag_process_as_gene": flag_proc,
            "process_terms_found": proc_terms,
            "flag_consistency_mismatch": flag_cons,
            "flag_source_misattribution": flag_src,
            "flag_fake_trap_bleed": flag_bleed,
            "bleed_traps": bleed_traps,
        }
        taxonomy.append(rec)

        if flag_proc:
            snippet = full_text[:80].replace("\n", " ")
            process_instances.append({
                "fact_id": row["fact_id"],
                "gene": gene,
                "process_terms": proc_terms,
                "snippet": snippet,
            })

    tax_df = pd.DataFrame(taxonomy)

    # ── Summary table ──
    categories = {
        "process_as_gene": "flag_process_as_gene",
        "consistency_mismatch": "flag_consistency_mismatch",
        "source_misattribution": "flag_source_misattribution",
        "fake_trap_bleed": "flag_fake_trap_bleed",
    }

    print(f"\nTrace error taxonomy:")
    print(f"  {'category':<25} {'n_flagged':>10} {'wrong_rate':>12}")
    print(f"  {'─'*50}")

    summary = {}
    for cat_name, col in categories.items():
        flagged = tax_df[tax_df[col] == True]
        n_flagged = len(flagged)
        wrong_rate = (1 - flagged["correct"]).mean() if n_flagged > 0 else 0.0
        print(f"  {cat_name:<25} {n_flagged:>10} {wrong_rate:>11.1%}")
        summary[cat_name] = {
            "n_flagged": n_flagged,
            "wrong_rate": round(float(wrong_rate), 4),
        }

    # ── Process-as-gene instances ──
    print(f"\nProcess-as-gene instances (first 20):")
    if process_instances:
        print(f"  {'fact_id':<10} {'gene':<12} {'process_terms':<30} snippet")
        print(f"  {'─'*80}")
        for inst in process_instances[:20]:
            terms_str = ", ".join(inst["process_terms"])[:28]
            print(f"  {inst['fact_id']:<10} {inst['gene']:<12} {terms_str:<30} {inst['snippet'][:40]}")
    else:
        print("  None found.")

    # Count unique process terms across all instances
    from collections import Counter
    all_terms = []
    for inst in process_instances:
        all_terms.extend(inst["process_terms"])
    term_counts = Counter(all_terms).most_common(10)
    if term_counts:
        print(f"\nTop process terms mistaken for genes:")
        for term, cnt in term_counts:
            print(f"  {term}: {cnt}")

    # ── Save outputs ──
    out_dir = args.outputs.parent
    json_out = {
        "n_rows_analyzed": len(tax_df),
        "error_taxonomy": summary,
        "process_instances": process_instances[:50],
        "top_process_terms": [{"term": t, "count": c} for t, c in term_counts],
    }
    json_path = out_dir / "trace_error_taxonomy.json"
    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2)

    md_path = out_dir / "trace_error_taxonomy.md"
    with open(md_path, "w") as md:
        md.write("# Trace Error Taxonomy\n\n")
        md.write(f"**Rows analysed:** {len(tax_df)}  \n\n")

        md.write("## Summary\n\n")
        md.write("| Category | N Flagged | Wrong Rate |\n|---|---|---|\n")
        for cat_name, rec in summary.items():
            md.write(f"| {cat_name} | {rec['n_flagged']} | {rec['wrong_rate']*100:.1f}% |\n")

        md.write("\n## Process-as-Gene Instances\n\n")
        md.write(
            "The model treats biological *processes* as if they were *gene symbols*, "
            "referencing them in factual claims about gene databases.\n\n"
        )
        if process_instances:
            md.write("| Fact ID | Gene | Process Terms Found | Output Snippet |\n")
            md.write("|---|---|---|---|\n")
            for inst in process_instances[:30]:
                terms_str = ", ".join(f"`{t}`" for t in inst["process_terms"])
                snippet = inst["snippet"].replace("|", "\\|")
                md.write(f"| {inst['fact_id']} | **{inst['gene']}** | {terms_str} | {snippet} |\n")
        else:
            md.write("_None detected._\n")

        if term_counts:
            md.write("\n### Top Process Terms\n\n")
            md.write("| Term | Count |\n|---|---|\n")
            for term, cnt in term_counts:
                md.write(f"| `{term}` | {cnt} |\n")

    print(f"\n[Done] → {json_path}, {md_path}")


if __name__ == "__main__":
    main()

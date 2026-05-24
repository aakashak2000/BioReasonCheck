"""
BioReasonCheck-FI · pipeline.py
Builds: cellage_ref.csv, opengenes_ref.csv, valid_genes.csv,
        facts.csv, benchmark_claims.csv, benchmark.jsonl
"""
import argparse
import csv
import hashlib
import io
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

CELLAGE_GENE_CANDIDATES = [
    "gene_symbol", "gene symbol",   # with space (CellAge actual column name)
    "gene", "symbol", "hgnc_symbol", "name", "gene_name",
]

HARD_NEGATIVES = [
    "GAPDH", "ACTB", "TUBB", "LDHA", "PKM", "ENO1", "TPI1",
    "ALDOA", "PGK1", "PGAM1", "FASN", "ACACA", "ACLY", "SUCLA2", "SDHA",
]
FAKE_TRAPS = ["AGEX1", "LNVT3", "SNRP9X", "FOXQ7L", "TERT2B"]
HOUSEKEEPING = [
    "GAPDH", "ACTB", "TUBB", "LDHA", "PKM", "ENO1", "TPI1",
    "ALDOA", "PGK1", "PGAM1", "FASN", "ACACA", "ACLY", "SUCLA2", "SDHA",
    "UQCRC1", "COX5A", "TIMM23", "VDAC1", "TOMM40",
]

SYSTEM_MSG = (
    "You are evaluating biological claims about aging and longevity genes "
    "against specific databases. Answer using only the exact format requested."
)


# ─────────────────────────── file readers ────────────────────────────────────

def _parse_tsv_quoted(path: Path, skip_dup_header: bool = False) -> pd.DataFrame:
    """Read tab-separated files where every field is double-quoted."""
    rows = []
    header = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = [p.strip('"') for p in line.split("\t")]
            if header is None:
                header = parts
                continue
            if skip_dup_header and parts == header:
                continue
            rows.append(parts)
    if header is None:
        raise ValueError(f"Empty file: {path}")
    # pad short rows
    rows = [r + [""] * (len(header) - len(r)) for r in rows if r]
    return pd.DataFrame(rows, columns=header)


def read_opengenes(path: Path) -> pd.DataFrame:
    """
    opengenes.csv: tab-sep, every field double-quoted.
    Header is a SINGLE quoted cell "hgnc\tconfidence_level", so pandas sees it
    as one column. We parse manually.
    """
    rows = []
    header = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = [p.strip('"') for p in line.split("\t")]
            if header is None:
                header = parts
                continue
            rows.append(parts)
    df = pd.DataFrame(rows, columns=header)
    df["hgnc"] = df["hgnc"].str.strip()
    df["confidence_level"] = df["confidence_level"].str.strip()
    return df


def read_gene_criteria(path: Path) -> pd.DataFrame:
    """gene-criteria.tsv: tab-sep, double-quoted, duplicate header row,
    criteria values additionally wrapped in single-quotes."""
    df = _parse_tsv_quoted(path, skip_dup_header=True)
    df = df[df["hgnc"] != "hgnc"]  # safety: drop any stray header rows
    df["criteria"] = df["criteria"].str.strip("'").str.strip()
    df["hgnc"] = df["hgnc"].str.strip()
    return df


def read_opengenes_lifespan(path: Path) -> pd.DataFrame:
    df = _parse_tsv_quoted(path, skip_dup_header=False)
    df["hgnc"] = df["hgnc"].str.strip()
    df["effect_on_lifespan"] = df["effect_on_lifespan"].str.strip()
    return df


# ─────────────────────────── step 1 ──────────────────────────────────────────

def step1_cellage(dry_run: bool, gene_col_override: str | None) -> pd.DataFrame:
    path = RAW / "cellage.csv"
    raw = pd.read_csv(path, sep="\t", dtype=str)
    raw.columns = [c.strip() for c in raw.columns]

    if gene_col_override:
        col = gene_col_override
        if col not in raw.columns:
            raise ValueError(f"--cellage-gene-col '{col}' not found. Available: {raw.columns.tolist()}")
    else:
        col = None
        raw_cols_lower = {c.lower(): c for c in raw.columns}
        for candidate in CELLAGE_GENE_CANDIDATES:
            if candidate in raw_cols_lower:
                col = raw_cols_lower[candidate]
                break
        if col is None:
            print(f"[ERROR] Cannot find gene column in CellAge. Available columns: {raw.columns.tolist()}")
            raise ValueError("CellAge gene column not found.")

    if dry_run:
        print(f"[DRY-RUN] CellAge: detected gene column = '{col}', "
              f"rows = {len(raw)}, unique genes = {raw[col].nunique()}")
        return pd.DataFrame()

    genes = raw[col].dropna().str.upper().str.strip().unique()
    ref = pd.DataFrame({"gene": sorted(set(genes)), "source": "CellAge"})
    out = OUT / "cellage_ref.csv"
    ref.to_csv(out, index=False)
    print(f"[Step 1] CellAge ref: {len(ref)} genes → {out}")
    return ref


# ─────────────────────────── step 2 ──────────────────────────────────────────

def _lifespan_vote(effects: list[str]) -> str:
    votes = []
    for e in effects:
        e_lower = e.lower()
        if "increases lifespan" in e_lower or "improves survival" in e_lower:
            votes.append("PRO")
        elif "decreases lifespan" in e_lower or "decreases survival" in e_lower:
            votes.append("ANTI")
        else:
            votes.append("NEUTRAL")
    if not votes:
        return "UNKNOWN"
    c = Counter(votes)
    top = c.most_common()
    if len(top) == 1 or top[0][1] > top[1][1]:
        return top[0][0]
    # tie between PRO and ANTI (or any real conflict)
    if c.get("PRO", 0) > 0 and c.get("ANTI", 0) > 0:
        return "MIXED"
    return top[0][0]


def step2_opengenes(dry_run: bool) -> pd.DataFrame:
    og = read_opengenes(RAW / "opengenes.csv")
    gc = read_gene_criteria(RAW / "gene-criteria.tsv")
    ls = read_opengenes_lifespan(RAW / "opengenes_lifespan.csv")

    if dry_run:
        print(f"[DRY-RUN] OpenGenes: {og['hgnc'].nunique()} genes, "
              f"{len(gc)} criteria rows, {len(ls)} lifespan rows")
        print(f"          Confidence levels: {og['confidence_level'].value_counts().to_dict()}")
        print(f"          Effect values: {ls['effect_on_lifespan'].value_counts().to_dict()}")
        return pd.DataFrame()

    # criteria per gene
    gc_grouped = defaultdict(set)
    for _, row in gc.iterrows():
        gc_grouped[row["hgnc"].upper()].add(row["criteria"])

    # lifespan vote per gene
    ls_grouped = defaultdict(list)
    for _, row in ls.iterrows():
        ls_grouped[row["hgnc"].upper()].append(row["effect_on_lifespan"])

    records = []
    for _, row in og.iterrows():
        gene = row["hgnc"].upper()
        conf = row["confidence_level"].lower().strip()
        tags = gc_grouped.get(gene, set())
        effects = ls_grouped.get(gene, [])
        lifespan_effect = _lifespan_vote(effects)

        lifespan_extending = (
            lifespan_effect == "PRO"
            or any("extend mammalian lifespan" in t.lower() for t in tags)
            or any("extend non-mammalian lifespan" in t.lower() for t in tags)
        )
        lifespan_reducing = (
            lifespan_effect == "ANTI"
            or any("reduce" in t.lower() and "lifespan" in t.lower() for t in tags)
            or any("decrease" in t.lower() and "lifespan" in t.lower() for t in tags)
        )

        records.append({
            "gene": gene,
            "confidence_level": conf,
            "lifespan_extending": lifespan_extending,
            "lifespan_reducing": lifespan_reducing,
            "lifespan_effect": lifespan_effect,
            "criteria_count": len(tags),
        })

    ref = pd.DataFrame(records).drop_duplicates("gene")
    out = OUT / "opengenes_ref.csv"
    ref.to_csv(out, index=False)
    print(f"[Step 2] OpenGenes ref: {len(ref)} genes → {out}")
    return ref


# ─────────────────────────── step 3 ──────────────────────────────────────────

def step3_valid_genes(cellage_ref: pd.DataFrame, og_ref: pd.DataFrame,
                      dry_run: bool) -> pd.DataFrame:
    if dry_run:
        return pd.DataFrame()

    ca_genes = set(cellage_ref["gene"].str.upper())
    og_genes = set(og_ref["gene"].str.upper())
    all_genes = ca_genes | og_genes | set(g.upper() for g in HOUSEKEEPING)

    records = [
        {
            "gene": g,
            "in_cellage": g in ca_genes,
            "in_opengenes": g in og_genes,
        }
        for g in sorted(all_genes)
    ]
    df = pd.DataFrame(records)
    out = OUT / "valid_genes.csv"
    df.to_csv(out, index=False)
    print(f"[Step 3] valid_genes: {len(df)} genes → {out}")
    return df


# ─────────────────────────── step 4 ──────────────────────────────────────────

def _train_test_split(gene: str) -> str:
    h = int(hashlib.md5(gene.encode()).hexdigest(), 16)
    return "train" if h % 10 < 7 else "test"


def _claim(gene: str, gene_type: str, og_row: pd.Series | None) -> str:
    if gene_type == "cellage":
        return f"{gene} is listed as a cellular senescence gene in CellAge."
    if gene_type == "og_extending":
        return (f"{gene} is listed in OpenGenes as a gene whose activity extends "
                "mammalian lifespan.")
    if gene_type == "og_mixed":
        conf = og_row["confidence_level"] if og_row is not None else "moderate"
        return (f"{gene} is listed in OpenGenes as associated with aging "
                f"(confidence: {conf}).")
    # hard_negative or fake_trap — claim is intentionally false
    return f"{gene} is listed as a cellular senescence gene in CellAge."


def step4_facts(cellage_ref: pd.DataFrame, og_ref: pd.DataFrame,
                dry_run: bool, seed: int) -> pd.DataFrame:
    if dry_run:
        return pd.DataFrame()

    rng = random.Random(seed)

    ca_genes = sorted(cellage_ref["gene"].str.upper().tolist())
    og_genes_set = set(og_ref["gene"].str.upper())

    # ── 15 CellAge genes: middle quintile by symbol length ──
    ca_by_len = sorted(ca_genes, key=len, reverse=True)
    n = len(ca_by_len)
    q2_start, q2_end = int(n * 0.4), int(n * 0.6)
    ca_pool = ca_by_len[q2_start:q2_end]
    if len(ca_pool) < 15:
        ca_pool = ca_by_len  # fallback
    rng.shuffle(ca_pool)
    selected_ca = ca_pool[:15]
    selected_ca_set = set(selected_ca)

    # ── 10 OpenGenes high/highest + lifespan_extending ──
    og_ext = og_ref[
        og_ref["confidence_level"].isin(["highest", "high"])
        & og_ref["lifespan_extending"].astype(bool)
        & ~og_ref["gene"].isin(selected_ca_set)
    ]["gene"].tolist()
    rng.shuffle(og_ext)
    selected_og_ext = og_ext[:10]

    already_selected = selected_ca_set | set(selected_og_ext)

    # ── 5 OpenGenes MIXED effect ──
    og_mixed = og_ref[
        (og_ref["lifespan_effect"] == "MIXED")
        & ~og_ref["gene"].isin(already_selected)
    ]["gene"].tolist()
    rng.shuffle(og_mixed)
    selected_og_mixed = og_mixed[:5]
    if len(selected_og_mixed) < 5:
        # fallback: any og gene not already used
        fallback = og_ref[~og_ref["gene"].isin(already_selected | set(selected_og_mixed))]["gene"].tolist()
        rng.shuffle(fallback)
        selected_og_mixed += fallback[:5 - len(selected_og_mixed)]

    already_selected |= set(selected_og_mixed)

    # ── 15 hard negatives ──
    hn_pool = [g for g in HARD_NEGATIVES if g.upper() not in already_selected]
    selected_hn = [g.upper() for g in hn_pool[:15]]

    # ── 5 fake traps ──
    selected_ft = [g.upper() for g in FAKE_TRAPS[:5]]

    og_dict = og_ref.set_index("gene").to_dict("index")

    records = []
    fact_num = 1

    def add(gene, gene_type, source_dataset, gold_label):
        nonlocal fact_num
        og_row = og_dict.get(gene)
        og_series = pd.Series(og_row) if og_row else None
        records.append({
            "fact_id": f"F{fact_num:03d}",
            "gene": gene,
            "source_dataset": source_dataset,
            "gene_type": gene_type,
            "gold_label": gold_label,
            "claim_text": _claim(gene, gene_type, og_series),
            "split": _train_test_split(gene),
        })
        fact_num += 1

    for g in selected_ca:
        add(g, "cellage", "CellAge", "SUPPORTED")
    for g in selected_og_ext:
        add(g, "og_extending", "OpenGenes", "SUPPORTED")
    for g in selected_og_mixed:
        add(g, "og_mixed", "OpenGenes", "INSUFFICIENT_EVIDENCE")
    for g in selected_hn:
        add(g, "hard_negative", "CellAge", "NOT_SUPPORTED")
    for g in selected_ft:
        add(g, "fake_trap", "CellAge", "NOT_SUPPORTED")

    df = pd.DataFrame(records)
    out = OUT / "facts.csv"
    df.to_csv(out, index=False)
    print(f"[Step 4] facts: {len(df)} total → {out}")
    print(f"         label distribution: {df['gold_label'].value_counts().to_dict()}")
    return df


# ─────────────────────────── step 5 ──────────────────────────────────────────

LETTERS = ["A", "B", "C", "D"]


def _build_mcq(fact_index: int, gene: str, source_dataset: str,
               claim_text: str, gold_label: str) -> dict:
    correct_pos = fact_index % 4  # 0=A,1=B,2=C,3=D
    trap = FAKE_TRAPS[fact_index % len(FAKE_TRAPS)]
    distractor_claim = claim_text.replace(gene, trap, 1)

    d1 = distractor_claim
    d2 = f"{gene} is a general metabolic gene with no aging annotation."
    d3 = f"The stated database does not contain an entry for {gene}."

    options = [d1, d2, d3]
    options.insert(correct_pos, claim_text)  # inject correct at right slot

    opt_dict = {LETTERS[i]: options[i] for i in range(4)}
    correct_option = LETTERS[correct_pos]

    prompt = (
        f"Which of the following statements is supported by {source_dataset}?\n"
        + "\n".join(f"{l}. {opt_dict[l]}" for l in LETTERS)
        + "\nAnswer with exactly one letter: A, B, C, or D."
    )
    return {"prompt": prompt, "correct_option": correct_option, "options": opt_dict}


def step5_benchmark_claims(facts: pd.DataFrame, dry_run: bool) -> pd.DataFrame:
    if dry_run:
        return pd.DataFrame()

    rows = []
    for fact_index, fact in facts.iterrows():
        base = {
            "fact_id": fact["fact_id"],
            "gene": fact["gene"],
            "source_dataset": fact["source_dataset"],
            "gene_type": fact["gene_type"],
            "gold_label": fact["gold_label"],
            "claim_text": fact["claim_text"],
            "split": fact["split"],
        }

        # ── BINARY ──
        binary_correct = "YES" if fact["gold_label"] == "SUPPORTED" else "NO"
        binary_prompt = (
            "Is the following claim supported by the stated database?\n"
            f"Claim: {fact['claim_text']}\n"
            "Answer with exactly one word: YES or NO."
        )
        rows.append({
            **base,
            "id": f"{fact['fact_id']}_binary",
            "format_type": "binary",
            "correct_answer": binary_correct,
            "correct_option": "",
            "prompt": binary_prompt,
        })

        # ── TERNARY ──
        ternary_prompt = (
            "Evaluate the following claim about aging biology.\n"
            f"Claim: {fact['claim_text']}\n"
            "Answer with exactly one of these three labels on the final line:\n"
            "SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_EVIDENCE"
        )
        rows.append({
            **base,
            "id": f"{fact['fact_id']}_ternary",
            "format_type": "ternary",
            "correct_answer": fact["gold_label"],
            "correct_option": "",
            "prompt": ternary_prompt,
        })

        # ── MCQ ──
        mcq = _build_mcq(
            fact_index, fact["gene"], fact["source_dataset"],
            fact["claim_text"], fact["gold_label"],
        )
        rows.append({
            **base,
            "id": f"{fact['fact_id']}_mcq",
            "format_type": "mcq",
            "correct_answer": fact["gold_label"],
            "correct_option": mcq["correct_option"],
            "prompt": mcq["prompt"],
        })

    df = pd.DataFrame(rows)
    out = OUT / "benchmark_claims.csv"
    df.to_csv(out, index=False)
    print(f"[Step 5] benchmark_claims: {len(df)} rows → {out}")
    return df


# ─────────────────────────── step 6 ──────────────────────────────────────────

def step6_benchmark_jsonl(claims: pd.DataFrame, dry_run: bool) -> None:
    if dry_run:
        return

    out = OUT / "benchmark.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for _, row in claims.iterrows():
            obj = {
                "id": row["id"],
                "fact_id": row["fact_id"],
                "gene": row["gene"],
                "format_type": row["format_type"],
                "split": row["split"],
                "gold_label": row["gold_label"],
                "correct_answer": row["correct_answer"],
                "correct_option": row["correct_option"],
                "messages": [
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user", "content": row["prompt"]},
                ],
            }
            f.write(json.dumps(obj) + "\n")
    print(f"[Step 6] benchmark.jsonl: {len(claims)} entries → {out}")


# ─────────────────────────── main ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BioReasonCheck-FI pipeline")
    parser.add_argument("--cellage-gene-col", default=None,
                        help="Override auto-detected CellAge gene column name")
    parser.add_argument("--opengenes-gene-col", default=None,
                        help="(Unused — OpenGenes uses 'hgnc' column)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print detected columns and counts; write nothing")
    parser.add_argument("--skip-facts", action="store_true",
                        help="Skip step 4 (facts.csv rebuild); use existing facts.csv for steps 5-6")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    cellage_ref = step1_cellage(args.dry_run, args.cellage_gene_col)
    og_ref = step2_opengenes(args.dry_run)

    if args.dry_run:
        print("[DRY-RUN] Complete — no files written.")
        return

    valid_genes = step3_valid_genes(cellage_ref, og_ref, args.dry_run)

    if args.skip_facts:
        facts_path = OUT / "facts.csv"
        if not facts_path.exists():
            print(f"[ERROR] --skip-facts set but {facts_path} not found. Run without --skip-facts first.")
            return
        facts = pd.read_csv(facts_path)
        print(f"[Step 4] Skipped — loaded existing facts.csv ({len(facts)} rows)")
    else:
        facts = step4_facts(cellage_ref, og_ref, args.dry_run, args.seed)

    claims = step5_benchmark_claims(facts, args.dry_run)
    step6_benchmark_jsonl(claims, args.dry_run)

    print("\n[Done] All outputs in:", OUT)


if __name__ == "__main__":
    main()

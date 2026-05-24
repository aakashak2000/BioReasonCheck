"""
BioReasonCheck-FI · update_facts.py
Applies 5 corrections to data/processed/facts.csv:
  1. Replace MTOR (F022) with FOXO3
  2. Fix og_mixed claim template
  3. Move AGEX1 + LNVT3 to test split
  4. Add 10 new INSUFFICIENT_EVIDENCE facts from OpenGenes MIXED genes
  5. Add 2 paraphrase variants for 15 selected facts
"""
import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
FACTS = ROOT / "data" / "processed" / "facts.csv"
OG_REF = ROOT / "data" / "processed" / "opengenes_ref.csv"


def split_by_hash(gene: str) -> str:
    return "train" if int(hashlib.md5(gene.encode()).hexdigest(), 16) % 10 < 7 else "test"


df = pd.read_csv(FACTS)
existing_genes = set(df["gene"].str.upper())

# ─── TASK 1: Replace MTOR with FOXO3 ────────────────────────────────────────
for candidate in ["FOXO3", "SIRT6"]:
    if candidate.upper() not in existing_genes:
        chosen = candidate
        break
else:
    chosen = "CYB5R3"

idx = df[df["fact_id"] == "F022"].index[0]
df.at[idx, "gene"] = chosen
df.at[idx, "source_dataset"] = "OpenGenes"
df.at[idx, "gene_type"] = "og_extending"
df.at[idx, "gold_label"] = "SUPPORTED"
df.at[idx, "claim_text"] = (
    f"{chosen} is listed in OpenGenes as a gene whose activity extends mammalian lifespan."
)
df.at[idx, "split"] = "train"
print(f"MTOR replaced with {chosen} in F022.")

# ─── TASK 2: Fix og_mixed claim template ─────────────────────────────────────
mixed_mask = df["gene_type"] == "og_mixed"
for i in df[mixed_mask].index:
    gene = df.at[i, "gene"]
    df.at[i, "claim_text"] = (
        f"{gene} has consistent, well-supported evidence of lifespan extension in OpenGenes."
    )
n_mixed = mixed_mask.sum()
print(f"og_mixed claim template updated for {n_mixed} facts.")

# ─── TASK 3: Move AGEX1 + LNVT3 to test split ───────────────────────────────
for gene in ["AGEX1", "LNVT3"]:
    mask = df["gene"] == gene
    df.loc[mask, "split"] = "test"
print("AGEX1 and LNVT3 moved to test split.")

counts = df.groupby(["gene_type", "split"]).size().unstack(fill_value=0)
print("\nSplit counts per gene_type:")
print(counts.to_string())

# ─── TASK 4: Add 10 new INSUFFICIENT_EVIDENCE facts ─────────────────────────
og_ref = pd.read_csv(OG_REF)
mixed_genes = og_ref[og_ref["lifespan_effect"] == "MIXED"]["gene"].str.upper().tolist()
existing_now = set(df["gene"].str.upper())

# Prefer high/highest confidence; exclude already present
conf_order = {"highest": 0, "high": 1, "moderate": 2, "low": 3}
candidates = og_ref[
    (og_ref["lifespan_effect"] == "MIXED") &
    (~og_ref["gene"].str.upper().isin(existing_now))
].copy()
candidates["conf_rank"] = candidates["confidence_level"].map(conf_order).fillna(9)
candidates = candidates.sort_values("conf_rank").reset_index(drop=True)
candidates = candidates.head(10)

if len(candidates) == 0:
    print("No new MIXED genes found — skipping Task 4.")
else:
    new_rows = []
    for i, row in candidates.iterrows():
        gene = row["gene"].upper()
        fid_num = 51 + i
        sp = split_by_hash(gene)
        new_rows.append({
            "fact_id": f"F{fid_num:03d}",
            "gene": gene,
            "source_dataset": "OpenGenes",
            "gene_type": "og_mixed",
            "gold_label": "INSUFFICIENT_EVIDENCE",
            "claim_text": f"{gene} has consistent, well-supported evidence of lifespan extension in OpenGenes.",
            "split": sp,
        })

    new_df = pd.DataFrame(new_rows)

    # Enforce at least 3 test facts
    test_count = (new_df["split"] == "test").sum()
    if test_count < 3:
        need = 3 - test_count
        train_rows = new_df[new_df["split"] == "train"].sort_values("gene").index[:need]
        new_df.loc[train_rows, "split"] = "test"

    df = pd.concat([df, new_df], ignore_index=True)
    n_test_new = (new_df["split"] == "test").sum()
    print(f"\nAdded {len(new_df)} new INSUFFICIENT_EVIDENCE facts. Test split gets {n_test_new}.")
    print("New genes:", ", ".join(new_df["gene"].tolist()))

# ─── TASK 5: Add 2 paraphrase variants for 15 selected facts ────────────────
PARAPHRASE_TEMPLATES = {
    "cellage": [
        lambda g: f"According to CellAge, {g} is associated with cellular senescence.",
        lambda g: f"CellAge database: is {g} catalogued as a senescence gene?",
    ],
    "og_extending": [
        lambda g: f"Based on OpenGenes data, {g} has evidence supporting lifespan extension.",
        lambda g: f"OpenGenes lists {g} among genes with lifespan-extending experimental support.",
    ],
    "hard_negative": [
        lambda g: f"According to CellAge, {g} is associated with cellular senescence.",
        lambda g: f"CellAge database: is {g} catalogued as a senescence gene?",
    ],
}

paraphrase_rows = []
for gtype, templates in PARAPHRASE_TEMPLATES.items():
    subset = df[(df["gene_type"] == gtype) & (~df["fact_id"].str.contains("_"))].head(5)
    for _, row in subset.iterrows():
        gene = row["gene"]
        for v_idx, tmpl in enumerate(templates, start=1):
            paraphrase_rows.append({
                "fact_id": f"{row['fact_id']}_v{v_idx}",
                "gene": gene,
                "source_dataset": row["source_dataset"],
                "gene_type": f"{gtype}_paraphrase",
                "gold_label": row["gold_label"],
                "claim_text": tmpl(gene),
                "split": row["split"],
            })

para_df = pd.DataFrame(paraphrase_rows)
df = pd.concat([df, para_df], ignore_index=True)
print(f"\nAdded {len(para_df)} paraphrase variants for 15 base facts.")

# ─── Save ────────────────────────────────────────────────────────────────────
df.to_csv(FACTS, index=False)
print(f"\nfacts.csv updated: {len(df)} total rows.")
print("\nFinal split counts:")
print(df.groupby(["gene_type", "split"]).size().unstack(fill_value=0).to_string())

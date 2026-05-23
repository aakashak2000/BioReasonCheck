"""
BioReasonCheck-FI · make_failure_gallery.py
Generates outputs/failure_gallery.md — a curated table of model failures
organised by failure type.

Failure types
─────────────
  format_flip   — model gets the same fact right in one format but wrong in another
  hallucinated  — model output contains a fake-trap symbol
  consistent_wrong — model is consistently wrong across ALL formats for a fact
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "data" / "processed"

FAKE_TRAPS = ["AGEX1", "LNVT3", "SNRP9X", "FOXQ7L", "TERT2B"]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def is_correct(row: dict) -> bool:
    fmt = row["format_type"]
    parsed = row["parsed_label"]
    if parsed == "UNPARSEABLE":
        return False
    if fmt == "binary":
        return parsed == row["correct_answer"]
    return parsed == row["gold_label"]


def contains_fake_trap(text: str) -> list[str]:
    found = []
    text_upper = text.upper()
    for ft in FAKE_TRAPS:
        if re.search(r"\b" + re.escape(ft) + r"\b", text_upper):
            found.append(ft)
    return found


def main():
    outputs_file = OUTPUTS / "model_outputs.jsonl"
    if not outputs_file.exists():
        print(f"[ERROR] {outputs_file} not found")
        return

    rows = load_jsonl(outputs_file)

    # Group by fact_id
    by_fact: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_fact[r["fact_id"]].append(r)

    format_flips = []      # (fact_id, gene, gold, formats_correct, formats_wrong)
    hallucinated = []      # (id, gene, format, gold, parsed, traps_found, snippet)
    consistent_wrong = []  # (fact_id, gene, gold, all_parsed)

    for fact_id, fact_rows in by_fact.items():
        gene = fact_rows[0]["gene"]
        gold = fact_rows[0]["gold_label"]

        correct_by_fmt = {}
        parsed_by_fmt = {}
        for r in fact_rows:
            fmt = r["format_type"]
            correct_by_fmt[fmt] = is_correct(r)
            parsed_by_fmt[fmt] = r["parsed_label"]

            # Hallucination check on raw_output
            raw = r.get("raw_output", "") or ""
            traps = contains_fake_trap(raw)
            if traps:
                hallucinated.append({
                    "id": r["id"],
                    "gene": gene,
                    "format": fmt,
                    "gold": gold,
                    "parsed": r["parsed_label"],
                    "traps": traps,
                    "snippet": raw[:300].replace("\n", " "),
                })

        n_formats = len(correct_by_fmt)
        n_correct = sum(correct_by_fmt.values())

        if n_formats >= 2 and 0 < n_correct < n_formats:
            # At least one right, at least one wrong → format flip
            fmts_right = [f for f, ok in correct_by_fmt.items() if ok]
            fmts_wrong = [f for f, ok in correct_by_fmt.items() if not ok]
            format_flips.append({
                "fact_id": fact_id,
                "gene": gene,
                "gold": gold,
                "correct_formats": fmts_right,
                "wrong_formats": fmts_wrong,
                "parsed_by_fmt": parsed_by_fmt,
            })
        elif n_correct == 0 and n_formats >= 2:
            consistent_wrong.append({
                "fact_id": fact_id,
                "gene": gene,
                "gold": gold,
                "parsed_by_fmt": parsed_by_fmt,
            })

    # ── Write gallery ──
    gallery_path = OUTPUTS / "failure_gallery.md"
    with open(gallery_path, "w", encoding="utf-8") as md:
        md.write("# BioReasonCheck-FI — Failure Gallery\n\n")
        md.write(
            "This gallery catalogues three categories of model failure. "
            "All examples come from the held-out **test** split unless "
            "otherwise noted.\n\n"
        )
        md.write(f"| Category | Count |\n")
        md.write(f"|---|---|\n")
        md.write(f"| Format flips (right in ≥1 format, wrong in ≥1 other) | {len(format_flips)} |\n")
        md.write(f"| Hallucinated fake-trap symbols in output | {len(hallucinated)} |\n")
        md.write(f"| Consistently wrong across all formats | {len(consistent_wrong)} |\n\n")

        # ── Section 1: Format flips ──
        md.write("---\n\n## 1. Format Flips\n\n")
        md.write(
            "The model answers **correctly in at least one format** but **incorrectly "
            "in at least one other format** for the same underlying fact. "
            "This is the core format-instability signal.\n\n"
        )
        md.write("| Fact ID | Gene | Gold Label | Correct Formats | Wrong Formats | Parsed Labels |\n")
        md.write("|---|---|---|---|---|---|\n")
        for f in format_flips[:30]:
            parsed_str = " / ".join(f"{k}:{v}" for k, v in sorted(f["parsed_by_fmt"].items()))
            md.write(
                f"| {f['fact_id']} | **{f['gene']}** | `{f['gold']}` "
                f"| {', '.join(f['correct_formats'])} "
                f"| {', '.join(f['wrong_formats'])} "
                f"| {parsed_str} |\n"
            )
        if len(format_flips) > 30:
            md.write(f"\n_... {len(format_flips) - 30} more format flips not shown._\n")

        # ── Section 2: Hallucinated fake traps ──
        md.write("\n---\n\n## 2. Hallucinated Fake-Trap Symbols\n\n")
        md.write(
            "The model mentioned one or more **invented gene symbols** "
            f"(`{'`, `'.join(FAKE_TRAPS)}`) in its output for rows about **real genes**. "
            "These symbols do not exist in CellAge or OpenGenes — any mention is a hallucination.\n\n"
        )
        if hallucinated:
            md.write("| Row ID | Gene | Format | Gold | Parsed | Fake Symbol(s) | Output Snippet |\n")
            md.write("|---|---|---|---|---|---|---|\n")
            for h in hallucinated[:20]:
                traps_str = ", ".join(f"`{t}`" for t in h["traps"])
                snippet = h["snippet"][:120].replace("|", "\\|")
                md.write(
                    f"| {h['id']} | **{h['gene']}** | {h['format']} "
                    f"| `{h['gold']}` | `{h['parsed']}` "
                    f"| {traps_str} | {snippet} |\n"
                )
            if len(hallucinated) > 20:
                md.write(f"\n_... {len(hallucinated) - 20} more hallucination events not shown._\n")
        else:
            md.write("_No fake-trap hallucinations detected in raw outputs._\n")

        # ── Section 3: Consistently wrong ──
        md.write("\n---\n\n## 3. Consistently Wrong Across All Formats\n\n")
        md.write(
            "The model gets the same fact **wrong in every format**. "
            "These failures are not format-instability (the model is consistently "
            "wrong) — they reveal knowledge gaps independent of framing.\n\n"
        )
        if consistent_wrong:
            md.write("| Fact ID | Gene | Gold Label | binary | ternary | mcq |\n")
            md.write("|---|---|---|---|---|---|\n")
            for c in consistent_wrong[:30]:
                p = c["parsed_by_fmt"]
                md.write(
                    f"| {c['fact_id']} | **{c['gene']}** | `{c['gold']}` "
                    f"| `{p.get('binary', '—')}` "
                    f"| `{p.get('ternary', '—')}` "
                    f"| `{p.get('mcq', '—')}` |\n"
                )
        else:
            md.write("_No facts were consistently wrong across all three formats._\n")

    print(f"[Done] Failure gallery → {gallery_path}")
    print(f"       Format flips:       {len(format_flips)}")
    print(f"       Hallucinations:     {len(hallucinated)}")
    print(f"       Consistent wrongs:  {len(consistent_wrong)}")


if __name__ == "__main__":
    main()

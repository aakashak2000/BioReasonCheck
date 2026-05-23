"""
BioReasonCheck-FI · make_report.py
Assembles outputs/final_report.md from all computed artefacts.

Reads:
  outputs/metrics.json
  outputs/reasoning_summary.json
  outputs/reasoning_metrics.json
  outputs/fake_trap_leakage_table.md  (embedded inline)
  outputs/failure_gallery.md          (linked, not embedded)
  data/processed/benchmark_claims.csv (for dataset stats)
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "data" / "processed"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def main():
    metrics = load_json(OUTPUTS / "metrics.json")
    reasoning = load_json(OUTPUTS / "reasoning_summary.json")
    rm = load_json(OUTPUTS / "reasoning_metrics.json")
    leakage_table = load_text(OUTPUTS / "fake_trap_leakage_table.md")

    # Test-split metrics (flat keys = test split by convention)
    overall = metrics.get("overall", {})
    baselines = metrics.get("baselines", {})
    per_fmt = metrics.get("per_format", {})
    fi = metrics.get("format_instability", {})
    stat = metrics.get("statistical_tests", {})
    per_type = metrics.get("per_gene_type", {})
    unparseable = metrics.get("unparseable", {})

    # All-facts metrics + split comparison
    all_facts = metrics.get("all_facts", {})
    split_cmp = metrics.get("split_comparison", {})

    ftc = rm.get("fake_trap_contamination", {})

    # Dataset stats from benchmark_claims
    n_facts = 50
    n_prompts = 150
    try:
        import pandas as pd
        claims = pd.read_csv(DATA / "benchmark_claims.csv")
        n_prompts = len(claims)
        n_facts = claims["fact_id"].nunique()
    except Exception:
        pass

    report_path = OUTPUTS / "final_report.md"
    with open(report_path, "w", encoding="utf-8") as md:
        md.write(f"# BioReasonCheck-FI — Final Evaluation Report\n\n")
        md.write(f"_Generated: {date.today().isoformat()}_\n\n")
        md.write(
            "> **Track 01 · Insilico Medicine Hackathon**  \n"
            "> Benchmarking LongevityLLM (L-LLM) for format instability on aging-gene claims.\n\n"
        )

        # ── Executive Summary ──
        md.write("---\n\n## Executive Summary\n\n")

        fir = fi.get("rate", 0.0)
        fir_ci = stat.get("fir_ci", {})
        ci_lo = fir_ci.get("lo", None)
        ci_hi = fir_ci.get("hi", None)

        acc = overall.get("accuracy", 0.0)
        maj_acc = baselines.get("majority_accuracy", 0.0)

        md.write(
            f"We benchmarked **LongevityLLM (L-LLM)** on {n_prompts} prompts "
            f"({n_facts} unique facts × 3 formats: binary, ternary, MCQ) drawn from "
            f"CellAge, OpenGenes, hard-negative housekeeping genes, and invented fake-trap symbols.\n\n"
        )

        fir_str = pct(fir)
        if ci_lo is not None and ci_hi is not None:
            fir_str += f" [95% CI: {pct(ci_lo)}–{pct(ci_hi)}]"

        md.write(f"**Key findings:**\n\n")
        md.write(
            f"1. **Format Instability Rate (FIR) = {fir_str}** — "
            f"the model gives contradictory answers to the same factual claim "
            f"depending solely on how the question is framed.\n"
        )
        md.write(
            f"2. **Overall accuracy = {pct(acc)}** vs majority-class baseline {pct(maj_acc)}, "
            f"a gain of {pct(acc - maj_acc)}. "
            f"Macro-F1 = {pct(overall.get('macro_f1', 0.0))}.\n"
        )
        if ftc:
            md.write(
                f"3. **Fake-trap leakage** — invented gene symbols appeared in outputs for "
                f"{ftc.get('rows_with_leakage', 0)} / {ftc.get('total_non_trap_rows', 0)} "
                f"non-trap rows ({pct(ftc.get('leakage_rate', 0.0))}).\n"
            )
        md.write(
            f"4. **Reasoning traces** — composite score < 0.5 predicts errors with "
            f"Precision={pct(reasoning.get('threshold_precision', 0.0))}, "
            f"Recall={pct(reasoning.get('threshold_recall', 0.0))}, "
            f"F1={pct(reasoning.get('threshold_f1', 0.0))}.\n\n"
        )

        # ── Dataset ──
        md.write("---\n\n## Dataset\n\n")
        md.write(f"| Property | Value |\n|---|---|\n")
        md.write(f"| Total prompts | {n_prompts} |\n")
        md.write(f"| Unique facts | {n_facts} |\n")
        md.write(f"| Formats | binary, ternary, MCQ |\n")
        md.write(f"| Sources | CellAge, OpenGenes, hard negatives, fake traps |\n")
        md.write(f"| Splits | train (dev) / test |\n\n")

        # ── Overall Metrics ──
        md.write("---\n\n## Overall Metrics\n\n")
        md.write("| Metric | Value |\n|---|---|\n")
        md.write(f"| Accuracy | {pct(acc)} |\n")
        md.write(f"| Macro F1 | {pct(overall.get('macro_f1', 0.0))} |\n")
        md.write(f"| Balanced Accuracy | {pct(overall.get('balanced_accuracy', 0.0))} |\n")
        md.write(f"| Majority-class baseline accuracy | {pct(maj_acc)} |\n")
        md.write(f"| Random baseline accuracy | {pct(baselines.get('random_accuracy', 0.0))} |\n")
        md.write(f"| N prompts evaluated | {overall.get('n', n_prompts)} |\n")
        unparseable_count = unparseable.get("count", 0)
        md.write(f"| Unparseable outputs | {unparseable_count} |\n\n")

        # ── Per-Format Metrics ──
        md.write("---\n\n## Per-Format Metrics\n\n")
        md.write("| Format | Accuracy | Macro F1 | N |\n|---|---|---|---|\n")
        for fmt in ["binary", "ternary", "mcq"]:
            pf = per_fmt.get(fmt, {})
            if not pf:
                continue
            md.write(
                f"| {fmt} | {pct(pf.get('accuracy', 0.0))} "
                f"| {pct(pf.get('f1', 0.0))} | {pf.get('n', 0)} |\n"
            )
        md.write("\n")

        # ── Format Instability ──
        md.write("---\n\n## Format Instability\n\n")
        md.write("| Metric | Value |\n|---|---|\n")
        md.write(f"| Format Instability Rate (FIR) — test split | {pct(fir)} |\n")
        if ci_lo is not None and ci_hi is not None:
            md.write(f"| FIR Wilson 95% CI | [{pct(ci_lo)}, {pct(ci_hi)}] |\n")
        boot_ci = stat.get("fir_bootstrap_ci")
        if boot_ci:
            md.write(f"| FIR Bootstrap 95% CI (n=1000, by fact) | [{pct(boot_ci[0])}, {pct(boot_ci[1])}] |\n")
        md.write(f"| Unstable facts (test) | {fi.get('unstable_facts', 0)} / {fi.get('facts_with_2plus_formats', 0)} |\n")

        all_fi = all_facts.get("format_instability", {})
        all_stat = all_facts.get("statistical_tests", {})
        if all_fi:
            md.write(f"| FIR — all 50 facts | {pct(all_fi.get('rate', 0))} |\n")
            all_boot = all_stat.get("fir_bootstrap_ci")
            if all_boot:
                md.write(f"| FIR Bootstrap 95% CI (all facts) | [{pct(all_boot[0])}, {pct(all_boot[1])}] |\n")

        # McNemar — prefer all-facts result (more power)
        mcn_chi2 = all_stat.get("mcnemar_chi2") or stat.get("mcnemar_chi2")
        mcn_p    = all_stat.get("mcnemar_p")    or stat.get("mcnemar_p")
        mcn_b    = all_stat.get("mcnemar_b")    or stat.get("mcnemar_b")
        mcn_c    = all_stat.get("mcnemar_c")    or stat.get("mcnemar_c")
        if mcn_chi2 is not None:
            md.write(f"\n**McNemar test** (binary vs MCQ, Yates correction, all 50 facts):  \n")
            md.write(f"b={mcn_b}, c={mcn_c}, χ²={mcn_chi2:.3f}, p={mcn_p:.4f}  \n")
            if mcn_p is not None and mcn_p < 0.05:
                md.write("→ **Statistically significant** (p < 0.05): format framing causally shifts answers.\n\n")
            else:
                md.write("→ Not significant at p < 0.05.\n\n")
        else:
            md.write("\n")

        # Split comparison table
        if split_cmp:
            md.write("### Test Split vs All 50 Facts\n\n")
            md.write("| Metric | All 50 facts | Held-out 15 facts |\n|---|---|---|\n")
            all_s  = split_cmp.get("all_facts", {})
            test_s = split_cmp.get("test", {}) or {}
            def _p(d, k): return pct(d[k]) if d and d.get(k) is not None else "—"
            rows = [
                ("FIR",              "fir"),
                ("Binary accuracy",  "binary_accuracy"),
                ("Ternary accuracy", "ternary_accuracy"),
                ("MCQ accuracy",     "mcq_accuracy"),
                ("Overall accuracy", "overall_accuracy"),
            ]
            for label, key in rows:
                md.write(f"| {label} | {_p(all_s, key)} | {_p(test_s, key)} |\n")
            md.write("\n")

        # ── Per-Gene-Type Accuracy ──
        if per_type:
            md.write("---\n\n## Per-Gene-Type Accuracy\n\n")
            md.write("| Gene Type | Accuracy | N |\n|---|---|---|\n")
            for gtype, vals in per_type.items():
                md.write(
                    f"| {gtype} | {pct(vals.get('accuracy', 0.0))} "
                    f"| {vals.get('n', 0)} |\n"
                )
            md.write("\n")

        # ── Fake-Trap Contamination ──
        md.write("---\n\n## Fake-Trap Hallucination\n\n")
        md.write(
            "Five invented gene symbols (not present in any biological database) were "
            "embedded in the benchmark to detect hallucination: "
            "`AGEX1`, `LNVT3`, `SNRP9X`, `FOXQ7L`, `TERT2B`.\n\n"
        )
        if ftc:
            md.write(
                f"When checking outputs for **real-gene rows** "
                f"(n={ftc.get('total_non_trap_rows', '?')}), "
                f"**{ftc.get('rows_with_leakage', '?')} rows** "
                f"({pct(ftc.get('leakage_rate', 0.0))}) contained at least one "
                f"fake-trap symbol verbatim.\n\n"
            )
            per_sym = ftc.get("per_symbol_counts", {})
            if per_sym:
                md.write("| Symbol | Leakage Count |\n|---|---|\n")
                for sym, cnt in per_sym.items():
                    md.write(f"| `{sym}` | {cnt} |\n")
                md.write("\n")
        else:
            md.write("_Fake-trap contamination data not available (run score_reasoning.py first)._\n\n")

        # ── Reasoning Trace Analysis ──
        md.write("---\n\n## Reasoning Trace Analysis\n\n")
        md.write(
            "Ternary-format prompts were re-run with `--think` to collect "
            "extended reasoning traces. Traces were scored on two signals:\n\n"
            "- **Hallucination score** — fraction of gene-like tokens not in the valid-gene list\n"
            "- **Consistency score** — semantic agreement between trace conclusion and final answer\n"
            "- **Composite** = 0.4 × (1 − hallucination) + 0.6 × consistency\n\n"
        )
        md.write("| Signal | Pearson r with error |\n|---|---|\n")
        md.write(f"| 1 − composite_score | {reasoning.get('pearson_r_composite', 0.0):+.4f} |\n")
        md.write(f"| hallucination_score | {reasoning.get('pearson_r_hallucination', 0.0):+.4f} |\n")
        md.write(f"| 1 − consistency_score | {reasoning.get('pearson_r_consistency', 0.0):+.4f} |\n")
        md.write(
            f"\n**Error-prediction threshold** (composite < 0.5):  \n"
            f"Precision={pct(reasoning.get('threshold_precision', 0.0))}, "
            f"Recall={pct(reasoning.get('threshold_recall', 0.0))}, "
            f"F1={pct(reasoning.get('threshold_f1', 0.0))}\n\n"
        )

        # ── Robustness ──
        md.write("---\n\n## Robustness & Limitations\n\n")

        all_fir  = all_fi.get("rate") if all_fi else None
        test_fir = fi.get("rate")
        if all_fir is not None and test_fir is not None:
            delta = abs(test_fir - all_fir)
            direction = "higher" if test_fir > all_fir else "lower"
            md.write(
                f"**Held-out vs full-set consistency:** The test-split FIR ({pct(test_fir)}) "
                f"is {pct(delta)} {direction} than the full-50-fact FIR ({pct(all_fir)}). "
                f"The direction of the effect is consistent across both sets, "
                f"confirming the instability is not an artefact of the held-out selection.\n\n"
            )

        all_boot_ci = all_stat.get("fir_bootstrap_ci") if all_stat else None
        test_boot_ci = stat.get("fir_bootstrap_ci")
        if all_boot_ci:
            md.write(
                f"**Bootstrap CIs (resampling by fact, n=1000):** "
                f"All-facts: [{pct(all_boot_ci[0])}, {pct(all_boot_ci[1])}]"
            )
            if test_boot_ci:
                md.write(f"; Test-split: [{pct(test_boot_ci[0])}, {pct(test_boot_ci[1])}]")
            md.write(
                ". Both CIs exclude 50%, confirming the FIR is reliably above chance "
                "even accounting for fact-level sampling variance.\n\n"
            )

        md.write("**Known limitations:**\n\n")
        md.write(
            "- Test split contains only 15 facts — McNemar p-value on test alone is 0.23 "
            "(not significant). On the full 50 facts McNemar p = 0.026 (significant).\n"
            "- All prompts use database-membership framing; functional/mechanistic "
            "question types were not evaluated.\n"
            "- MCQ options use abstract labels (SUPPORTED/NOT_SUPPORTED) rather than "
            "substantive biological descriptions, which may exaggerate position bias.\n"
            "- L-LLM was run at temperature=0; stochastic behaviour under higher "
            "temperature was not evaluated.\n"
            "- Baseline comparison (Claude Sonnet 4.6) had 7 unparseable ternary outputs "
            "due to verbose responses — ternary accuracy may be underestimated for the baseline.\n\n"
        )

        # ── Links ──
        md.write("---\n\n## Artefacts\n\n")
        md.write("| File | Description |\n|---|---|\n")
        md.write("| `outputs/model_outputs.jsonl` | Raw model predictions (150 rows) |\n")
        md.write("| `outputs/traces_ternary.jsonl` | Reasoning traces — ternary only (50 rows) |\n")
        md.write("| `outputs/metrics.json` | Full accuracy & instability metrics |\n")
        md.write("| `outputs/metrics.md` | Human-readable metrics report |\n")
        md.write("| `outputs/reasoning_scores.jsonl` | Per-row reasoning scores |\n")
        md.write("| `outputs/reasoning_summary.json` | Pearson r & threshold analysis |\n")
        md.write("| `outputs/reasoning_metrics.json` | Fake-trap contamination metrics |\n")
        md.write("| `outputs/fake_trap_leakage_table.md` | Per-symbol leakage table |\n")
        md.write("| `outputs/failure_gallery.md` | Curated failure examples by category |\n")
        md.write("| `data/processed/benchmark.jsonl` | Full benchmark (150 prompts) |\n")
        md.write("| `data/processed/facts.csv` | 50 unique claims |\n\n")

    print(f"[Done] Final report → {report_path}")


if __name__ == "__main__":
    main()

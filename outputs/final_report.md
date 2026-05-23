# BioReasonCheck-FI — Final Evaluation Report

_Generated: 2026-05-23_

> **Track 01 · Insilico Medicine Hackathon**  
> Benchmarking LongevityLLM (L-LLM) for format instability on aging-gene claims.

---

## Executive Summary

We benchmarked **LongevityLLM (L-LLM)** on 150 prompts (50 unique facts × 3 formats: binary, ternary, MCQ) drawn from CellAge, OpenGenes, hard-negative housekeeping genes, and invented fake-trap symbols.

**Key findings:**

1. **Format Instability Rate (FIR) = 93.3%** — the model gives contradictory answers to the same factual claim depending solely on how the question is framed.
2. **Overall accuracy = 46.7%** vs majority-class baseline 46.7%, a gain of 0.0%. Macro-F1 = 33.2%.
3. **Fake-trap leakage** — invented gene symbols appeared in outputs for 0 / 45 non-trap rows (0.0%).
4. **Reasoning traces** — composite score < 0.5 predicts errors with Precision=55.0%, Recall=84.6%, F1=66.7%.

---

## Dataset

| Property | Value |
|---|---|
| Total prompts | 150 |
| Unique facts | 50 |
| Formats | binary, ternary, MCQ |
| Sources | CellAge, OpenGenes, hard negatives, fake traps |
| Splits | train (dev) / test |

---

## Overall Metrics

| Metric | Value |
|---|---|
| Accuracy | 46.7% |
| Macro F1 | 33.2% |
| Balanced Accuracy | 36.5% |
| Majority-class baseline accuracy | 46.7% |
| Random baseline accuracy | 33.3% |
| N prompts evaluated | 15 |
| Unparseable outputs | 0 |

---

## Per-Format Metrics

| Format | Accuracy | Macro F1 | N |
|---|---|---|---|
| binary | 66.7% | 28.6% | 15 |
| ternary | 46.7% | 33.2% | 15 |
| mcq | 33.3% | 33.3% | 15 |

---

## Format Instability

| Metric | Value |
|---|---|
| Format Instability Rate (FIR) | 93.3% |
| Unstable facts | 14 |
| Facts with ≥2 formats | 15 |

---

## Per-Gene-Type Accuracy

| Gene Type | Accuracy | N |
|---|---|---|
| cellage | 55.6% | 9 |
| hard_negative | 52.4% | 21 |
| og_extending | 33.3% | 9 |
| og_mixed | 50.0% | 6 |

---

## Fake-Trap Hallucination

Five invented gene symbols (not present in any biological database) were embedded in the benchmark to detect hallucination: `AGEX1`, `LNVT3`, `SNRP9X`, `FOXQ7L`, `TERT2B`.

When checking outputs for **real-gene rows** (n=45), **0 rows** (0.0%) contained at least one fake-trap symbol verbatim.

| Symbol | Leakage Count |
|---|---|
| `AGEX1` | 0 |
| `LNVT3` | 0 |
| `SNRP9X` | 0 |
| `FOXQ7L` | 0 |
| `TERT2B` | 0 |

---

## Reasoning Trace Analysis

Ternary-format prompts were re-run with `--think` to collect extended reasoning traces. Traces were scored on two signals:

- **Hallucination score** — fraction of gene-like tokens not in the valid-gene list
- **Consistency score** — semantic agreement between trace conclusion and final answer
- **Composite** = 0.4 × (1 − hallucination) + 0.6 × consistency

| Signal | Pearson r with error |
|---|---|
| 1 − composite_score | +0.0411 |
| hallucination_score | -0.2429 |
| 1 − consistency_score | +0.2184 |

**Error-prediction threshold** (composite < 0.5):  
Precision=55.0%, Recall=84.6%, F1=66.7%

---

## Artefacts

| File | Description |
|---|---|
| `outputs/model_outputs.jsonl` | Raw model predictions (150 rows) |
| `outputs/traces_ternary.jsonl` | Reasoning traces — ternary only (50 rows) |
| `outputs/metrics.json` | Full accuracy & instability metrics |
| `outputs/metrics.md` | Human-readable metrics report |
| `outputs/reasoning_scores.jsonl` | Per-row reasoning scores |
| `outputs/reasoning_summary.json` | Pearson r & threshold analysis |
| `outputs/reasoning_metrics.json` | Fake-trap contamination metrics |
| `outputs/fake_trap_leakage_table.md` | Per-symbol leakage table |
| `outputs/failure_gallery.md` | Curated failure examples by category |
| `data/processed/benchmark.jsonl` | Full benchmark (150 prompts) |
| `data/processed/facts.csv` | 50 unique claims |


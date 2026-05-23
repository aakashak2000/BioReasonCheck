# BioReasonCheck-FI

**Track 01 · Insilico Medicine Hackathon**

Benchmarking LongevityLLM (L-LLM) for **format instability** on aging-gene factual claims.

## Overview

We pose the same biological claim in three question formats — binary YES/NO, ternary 3-class, and MCQ — and measure how often LongevityLLM gives contradictory answers based on format framing alone.

**Headline result:** Format Instability Rate (FIR) = **93.3%** of test facts answered differently across formats.

## Repository Structure

```
scripts/
  pipeline.py           Build benchmark from CellAge + OpenGenes raw data
  run_llm.py            Run benchmark against L-LLM endpoint
  evaluate.py           Compute accuracy, FIR, Wilson CI, McNemar, per-gene-type
  score_reasoning.py    Score reasoning traces; fake-trap contamination analysis
  make_failure_gallery.py  Generate curated failure examples
  make_report.py        Assemble final_report.md from all artefacts

data/
  raw/                  cellage.csv, opengenes.csv, gene-criteria.tsv, ...
  processed/            benchmark.jsonl (150 prompts), facts.csv, benchmark_claims.csv

outputs/
  model_outputs.jsonl   Raw model predictions (150 rows)
  traces_ternary.jsonl  Reasoning traces, ternary only (50 rows)
  metrics.json          Full evaluation metrics
  metrics.md            Human-readable metrics report
  reasoning_scores.jsonl  Per-row reasoning scores
  reasoning_metrics.json  Fake-trap contamination metrics
  failure_gallery.md    Curated failure examples by category
  final_report.md       Complete evaluation report
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in HF_ENDPOINT_URL and HF_ACCESS_TOKEN
```

## Running the Full Pipeline

```bash
# 1. Build benchmark dataset
python scripts/pipeline.py

# 2. Run model on all 150 prompts
python scripts/run_llm.py

# 3. (Optional) Collect reasoning traces on ternary format
python scripts/run_llm.py --think --format-filter ternary \
    --output outputs/traces_ternary.jsonl

# 4. Evaluate and score
python scripts/evaluate.py
python scripts/score_reasoning.py --outputs outputs/traces_ternary.jsonl \
    --out outputs/reasoning_scores.jsonl

# 5. Generate reports
python scripts/make_failure_gallery.py
python scripts/make_report.py
```

---

## Final Analysis Commands

Run these four scripts in order after `run_llm.py` has completed to reproduce all evaluation artefacts:

```bash
# Step 1 — Compute accuracy, FIR, Wilson CI, McNemar test, per-gene-type breakdown
python scripts/evaluate.py

# Step 2 — Score reasoning traces; quantify fake-trap hallucination contamination
python scripts/score_reasoning.py \
    --outputs outputs/traces_ternary.jsonl \
    --out outputs/reasoning_scores.jsonl

# Step 3 — Build failure gallery (format flips, hallucinations, consistent errors)
python scripts/make_failure_gallery.py

# Step 4 — Assemble final report from all artefacts
python scripts/make_report.py
```

**Expected outputs after running all four:**

| File | Description |
|---|---|
| `outputs/metrics.json` | Accuracy, FIR, Wilson CI, McNemar, per-gene-type |
| `outputs/metrics.md` | Human-readable version of metrics.json |
| `outputs/reasoning_scores.jsonl` | Per-row hallucination/consistency/composite scores |
| `outputs/reasoning_metrics.json` | Fake-trap contamination counts and leakage rate |
| `outputs/fake_trap_leakage_table.md` | Per-symbol leakage table |
| `outputs/failure_gallery.md` | Curated failure examples by category |
| `outputs/final_report.md` | Complete evaluation report |

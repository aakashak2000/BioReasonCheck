# BioReasonCheck-FI

**Format instability benchmark for LongevityLLM · Hackathon 2025 Track 01**

> **Key finding:** LongevityLLM answers the same biological claim differently in **14 of 15 cases** when the question format changes from binary → ternary → MCQ.  
> Format Instability Rate = **93.3%** [Bootstrap CI: 80%–100%]

---

## Results at a glance

| Metric | Value |
|---|---|
| Format Instability Rate (test) | **93.3%** |
| Binary accuracy | 67% |
| Ternary accuracy | 47% |
| MCQ accuracy | 33% |
| Majority-class baseline | 47% |
| L-LLM vs Claude Sonnet 4.6 FIR | 74% vs 40% |

Pre-computed results are in `outputs/`. You can read them without running anything.

---

## Setup

```bash
git clone https://github.com/aakashak2000/BioReasonCheck.git
cd BioReasonCheck
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in HF_ENDPOINT_URL and HF_ACCESS_TOKEN in .env
```

---

## Reproduce from scratch

```bash
# 1. Build benchmark dataset (50 facts × 3 formats = 150 prompts)
python scripts/pipeline.py

# 2. Run LongevityLLM on all 150 prompts
python scripts/run_llm.py

# 3. (Optional) Collect reasoning traces — ternary format only, think mode on
python scripts/run_llm.py --think --format-filter ternary \
    --output outputs/traces_ternary.jsonl

# 4. Evaluate
python scripts/evaluate.py
python scripts/evaluate.py --split all

# 5. Score reasoning traces
python scripts/score_reasoning.py \
    --outputs outputs/traces_ternary.jsonl \
    --out outputs/reasoning_scores.jsonl

# 6. Deep-dive analyses
python scripts/analyze_label_bias.py
python scripts/analyze_gene_category.py
python scripts/analyze_mcq_position.py
python scripts/analyze_trace_errors.py

# 7. Generate final report
python scripts/make_failure_gallery.py
python scripts/make_report.py
```

---

## Repository structure

```
scripts/
  pipeline.py               Build benchmark from CellAge + OpenGenes raw data
  run_llm.py                Query LongevityLLM endpoint (150 prompts)
  evaluate.py               FIR, accuracy, Wilson CI, McNemar, bootstrap CI
  score_reasoning.py        Score reasoning traces; fake-trap contamination
  analyze_label_bias.py     Label distribution, FP/FN rates, flip matrix
  analyze_gene_category.py  Per-gene-type accuracy + FIR
  analyze_mcq_position.py   MCQ position bias + chi-square test
  analyze_trace_errors.py   Process-as-gene, consistency mismatch taxonomy
  run_baseline_model.py     Compare vs any OpenAI-compatible baseline
  make_failure_gallery.py   Curated failure examples by category
  make_report.py            Assemble outputs/final_report.md

data/
  raw/                      CellAge, OpenGenes source files
  processed/                benchmark.jsonl, facts.csv (pre-built)

outputs/                    All pre-computed results (metrics, traces, reports)
```

---

## Benchmark design

**50 facts** across 4 gene categories:

| Category | N facts | Gold label | Description |
|---|---|---|---|
| CellAge senescence genes | 15 | SUPPORTED | Real aging genes |
| OpenGenes lifespan-extending | 10 | SUPPORTED | High-confidence longevity genes |
| OpenGenes mixed evidence | 5 | INSUFFICIENT_EVIDENCE | Contradictory findings |
| Hard negatives (housekeeping) | 15 | NOT_SUPPORTED | Real genes, no aging link |
| Fake traps | 5 | NOT_SUPPORTED | Invented gene symbols |

Each fact posed in 3 formats → **150 total prompts**. Train/test split: 35/15 facts.

---

## Baseline comparison

Set `BASELINE_ENDPOINT_URL`, `BASELINE_API_TOKEN`, and `BASELINE_MODEL_NAME` in `.env`, then:

```bash
python scripts/run_baseline_model.py
```

Supports any OpenAI-compatible endpoint and the Anthropic API.

# BioReasonCheck-FI — Pitch Document
## Hackathon 2025 · Track 01 · LongevityLLM Benchmarking

---

## Opening Hook (30 seconds)

"We asked LongevityLLM the same question about CDKN2A — one of the most well-known aging genes — three times. In binary format it said NO. In ternary format it said NOT_SUPPORTED. In multiple choice it said SUPPORTED. The gene didn't change. The biology didn't change. Only the question format changed. And in 14 out of 15 test cases, the model gave contradictory answers."

---

## The Problem (1 minute)

LongevityLLM is being positioned as a knowledge source for aging biology research. Researchers and tools will query it in different ways — a chatbot interface uses one format, a structured pipeline uses another, a form-based tool uses MCQ. If the model's answer depends on the format rather than the fact, it is not a reliable knowledge source. It's a format matcher.

No one had tested this systematically. We built the test.

---

## What We Built (2 minutes)

**BioReasonCheck-FI** — a format instability benchmark for LongevityLLM.

**The dataset:** 50 biological facts drawn from two curated databases:
- CellAge (866 human cellular senescence genes)
- OpenGenes (2,405 longevity genes with experimental evidence)

We added two adversarial categories:
- 15 **hard negatives** — real housekeeping genes (GAPDH, ACTB) with no aging link, to test false positive rate
- 5 **fake traps** — completely invented gene symbols that don't exist anywhere, to detect hallucination

Each fact was posed in three formats → **150 total prompts**.

**The infrastructure:** End-to-end Python pipeline — data ingestion, benchmark construction, model runner, evaluation, reasoning trace scorer, 5 deep-dive analysis scripts, and automated report generation. Everything is reproducible from a single `git clone`.

---

## The Results (2 minutes)

**Headline: Format Instability Rate = 93.3%**

14 of 15 held-out test facts got different correctness outcomes depending on format. Bootstrap confidence interval: 80%–100%. This is not noise.

**The mechanism is label bias:**
- Binary format: the model says NOT\_SUPPORTED 93% of the time regardless of the correct answer
- MCQ format: the model says SUPPORTED 67% of the time
- Same facts. The format decides the answer.

**MCQ position bias (p=0.033):** The model never selects option D. Not once. If the correct answer is in position D or B, the model always gets it wrong.

**Process-as-gene confusion:** The model mentioned "SENESCENCE" 43 times in its outputs as if it were a gene name. It's a biological process. This appears in 47 of 150 outputs — a systematic confusion between entities and processes.

**Consistency mismatch:** In 14 cases, the model's own reasoning trace correctly identifies the answer, then the output contradicts it. These cases have a 71% error rate — the model thinks one thing and writes another.

**Baseline comparison:** We ran the same 45 test prompts through Claude Sonnet 4.6 — a general model with no aging biology training. Claude got every MCQ correct (100% vs L-LLM's 30%). Claude's Format Instability Rate was 40% vs L-LLM's 74%. Domain specialization is making format instability worse, not better.

---

## Why This Matters (1 minute)

If a researcher uses LongevityLLM to screen 10,000 genes for longevity relevance, and the answer they get depends on which tool prompted the model, they will get different results from the same model depending on their interface. That's not a minor issue — that's reproducibility failure.

The overall accuracy of 47% matches the majority-class baseline exactly. The model is not using its biology knowledge — it is using format cues as a proxy for the answer. This is a fundamental reliability problem for any downstream application.

---

## Recommendations (30 seconds)

Four concrete fixes for Insilico Medicine:

1. **Don't use binary format** for L-LLM fact retrieval
2. **Rotate or avoid MCQ positions** — the model has a strong positional preference
3. **Use reasoning consistency as a confidence filter** — disagreement between trace and output predicts 71% of errors
4. **Add FIR as a standard metric** in any future L-LLM evaluation or fine-tuning pipeline

---

## Closing

We built a complete, reproducible benchmark that reveals a systematic reliability problem in LongevityLLM that no prior evaluation had caught. The code is open-source, the findings are statistically validated, and the recommendations are actionable today.

**GitHub:** https://github.com/aakashak2000/BioReasonCheck

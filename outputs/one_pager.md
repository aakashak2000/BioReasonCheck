# BioReasonCheck
### Format Instability Benchmark for LongevityLLM
**Track 01 · Insilico Medicine Hackathon 2026**

GitHub: https://github.com/aakashak2000/BioReasonCheck

---

## The Problem

LongevityLLM gives contradictory answers to the same biological fact depending on how the question is framed. A binary API call, a ternary classifier, and an MCQ interface can return opposite verdicts for the same gene — not because the biology changed, but because the prompt shape did. No prior evaluation had measured this. We built the test.

---

## What We Built

**270-prompt benchmark** grounded in CellAge and OpenGenes database exports — not PubMed abstracts, not Wikipedia.

- **60 unique genes** across 5 categories: confirmed senescence (CellAge), lifespan-extending (OpenGenes), mixed-evidence, metabolic hard negatives, and invented hallucination traps
- **3 structurally distinct formats per fact:** binary (YES/NO), ternary (3-class label), MCQ (4-option, correct position rotated)
- **Pre-registered test split** assigned by deterministic gene hash before any analysis ran — prevents metric tuning to reported results

**Diversity across three axes:**
- *Data:* 5 gene categories from confirmed positives to hallucination traps
- *Semantic:* 3 claim templates + paraphrase variants; Paraphrase Instability Rate measured formally
- *Format:* binary / ternary / MCQ — three different output generation strategies

---

## Key Results

| Metric | Value |
|---|---|
| **Format Instability Rate (pre-registered test)** | **95.0%** [Bootstrap CI: 85%–100%] |
| FIR — all 60 genes | 76.7% [Wilson CI: 65%–86%] |
| Ternary accuracy vs majority-class baseline | 38.5% vs 42.3% |
| McNemar p-value (all 60 genes) | **0.021** |
| Cohen's κ — binary vs MCQ | **−0.328** (worse than chance) |
| Cramér's V — format vs predicted label | **0.760** (very strong association) |
| Consistency mismatch error rate | **72.7%** (22 cases) |
| Claude Sonnet 4.6 MCQ vs L-LLM MCQ | **84.6% vs 34.6%** |

---

## The Mechanism

**Format dictates the label. Biology is irrelevant.**

- Binary triggers NOT_SUPPORTED **92%** of the time → false negative rate **83%**
- MCQ triggers SUPPORTED **81%** of the time → false positive rate **86%**
- Cramér's V = **0.760**: format alone predicts the label choice with very strong effect size
- Cohen's κ = **−0.328** (binary vs MCQ): formats are statistically independent — worse than chance agreement

**Fine-tuning amplified format sensitivity.** Claude Sonnet 4.6 with no aging biology training achieves 84.6% MCQ accuracy vs L-LLM's 34.6%. Domain specialisation made format instability worse, not better.

---

## The Reasoning Scorer

Automatic error detector using the model's own chain-of-thought — no human labels needed.

- **Process-as-gene confusion:** SENESCENCE used as a gene symbol in **78%** of ternary traces
- **Consistency mismatch:** 22 cases where reasoning concludes correctly but output contradicts it → **72.7% error rate**
- **Operational metric:** Scorer recall = 85%, F1 = 0.694 — deployable as a runtime filter today
- Each flagged trace = a ready DPO preference pair for future fine-tuning

---

## Recommendations for Insilico Medicine

1. **Avoid binary format** for L-LLM gene fact retrieval — systematic NOT_SUPPORTED bias regardless of true label
2. **Rotate MCQ option positions** in all deployed interfaces — model applies strong positional heuristics
3. **Deploy consistency scorer as runtime filter** — flags 85% of errors automatically, no annotation needed
4. **Add FIR as a standard metric** in all future L-LLM fine-tuning runs alongside accuracy

---

## Stack

Python · pandas · scipy · scikit-learn · HuggingFace Inference API · CellAge · OpenGenes · Anthropic API (Claude Sonnet 4.6 baseline)

**GitHub:** https://github.com/aakashak2000/BioReasonCheck

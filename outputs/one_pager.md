# BioReasonCheck-FI
## A Format Instability Benchmark for LongevityLLM

**Hackathon 2025 · Track 01 · LongevityLLM Benchmarking**  
GitHub: https://github.com/aakashak2000/BioReasonCheck

---

### The Problem

LongevityLLM is a specialist AI model for aging biology. But does it give consistent answers, or does it change its answer depending on *how* the question is framed? A model that contradicts itself based on format cannot be trusted as a scientific knowledge source.

---

### What We Built

A benchmark of **150 prompts** (50 biological facts × 3 question formats) drawn from CellAge and OpenGenes — two curated aging-gene databases. Each fact is posed as:
- **Binary** — "Answer YES or NO"
- **Ternary** — "Classify: SUPPORTED / NOT\_SUPPORTED / INSUFFICIENT\_EVIDENCE"
- **MCQ** — "Choose A / B / C / D"

We also embedded 5 **fake gene symbols** (AGEX1, LNVT3, SNRP9X, FOXQ7L, TERT2B) to detect hallucination, and 15 **housekeeping genes** (GAPDH, ACTB, FASN) as hard negatives.

---

### Key Results

| Metric | Value |
|---|---|
| **Format Instability Rate** | **93.3%** [Bootstrap CI: 80%–100%] |
| Binary accuracy | 67% |
| Ternary accuracy | 47% |
| MCQ accuracy | 33% |
| Overall vs majority baseline | 47% vs 47% |
| McNemar test (all 50 facts) | χ²=4.97, **p=0.026** |

**The model matches the majority-class baseline** — format framing, not biology knowledge, determines its answers.

---

### What Drives the Instability

**Label bias:** In binary format, the model says NOT\_SUPPORTED 93% of the time. In MCQ format, it says SUPPORTED 67% of the time. Same facts. The format alone flips the answer.

**MCQ position bias:** The model never selects option D (0/15). Chi-square p=0.033. Accuracy for positions B and D: 0%.

**Process-as-gene confusion:** "SENESCENCE" appears in 43/150 outputs as if it were a gene name. SASP appears 12 times similarly.

**Consistency mismatch:** In 14 cases, the model's reasoning reaches the correct conclusion but the final output is wrong — 71% error rate in this category.

---

### Baseline Comparison — Claude Sonnet 4.6

| Metric | LongevityLLM | Claude Sonnet 4.6 |
|---|---|---|
| MCQ accuracy | 30% | **100%** |
| Format Instability Rate | 74% | **40%** |
| Ternary accuracy | 50% | 50% |

A general-purpose model with no aging biology training is substantially more format-stable than the specialist model.

---

### Recommendations for Insilico Medicine

1. **Avoid binary format** for L-LLM fact retrieval — systematic NOT\_SUPPORTED bias makes it unreliable
2. **Rotate MCQ positions** or avoid MCQ — model refuses to select B or D
3. **Use consistency score as a filter** — reasoning contradicting its own output predicts 71% of errors
4. **Add FIR as a standard eval metric** for any future fine-tuning of L-LLM

---

### Tech Stack

Python · HuggingFace Inference Endpoints · CellAge · OpenGenes · scikit-learn · scipy · pandas · Anthropic API (baseline)

**All code, data, and outputs:** https://github.com/aakashak2000/BioReasonCheck

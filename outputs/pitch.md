# BioReasonCheck — Pitch Deck
## Track 01 · Insilico Medicine Hackathon 2026
**Total time: 5 minutes**

GitHub: https://github.com/aakashak2000/BioReasonCheck

---

## Slide 1 — The Problem (~30 seconds)

**Headline:** LongevityLLM answers the same biological fact differently depending on how you ask the question.

**Body:**
- L-LLM is Insilico Medicine's fine-tuned model for aging biology — used for target identification and gene screening
- Real pipelines query the same model in different formats: binary API calls, structured classifiers, MCQ interfaces
- If the answer changes based on format alone, the model cannot be trusted as a knowledge source
- No one had tested this systematically. We built the test.

**Speaker note:** Open with the doctor analogy: "Imagine asking a specialist — does this patient have condition X? They say no. You show them a form with the same question as multiple choice. They circle yes. Same specialist. Same patient. Same biology. That's what we found with LongevityLLM. In 19 of 20 test cases."

---

## Slide 2 — What We Built (~30 seconds)

**Headline:** 60 aging-gene facts × 3 formats = 270 prompts across 5 gene categories.

**Body:**
- 5 gene categories: CellAge senescence, OpenGenes lifespan-extending, mixed evidence, metabolic hard negatives, invented fake-trap genes
- 3 formats: binary (YES/NO), ternary (3-class label), MCQ (rotated correct position)
- Ground truth from CellAge and OpenGenes database exports — not PubMed abstracts, not Wikipedia
- Deterministic gene-hash split assigned before any analysis ran — pre-registered test set

**Speaker note:** "We pulled real genes from two specialist databases — CellAge and OpenGenes — and included invented gene symbols that don't exist anywhere: AGEX1, LNVT3. If the model confidently answers about those, it's hallucinating. We also included housekeeping genes like GAPDH — real genes, no aging link — to measure false positive rate. And 15 genes with genuinely contradictory evidence in OpenGenes, where the right answer is 'insufficient evidence.' That's a hard question that requires reasoning, not retrieval."

---

## Slide 3 — The Headline Finding (~45 seconds)

**Headline:** 95% Format Instability Rate. Same gene. Same biology. Different format, different answer.

**Body:**
- Format Instability Rate = **95.0%** [Bootstrap CI: 85%–100%]
- 19 of 20 pre-registered test facts: correct in one format, wrong in another
- McNemar test (all 60 genes): χ² = 5.35, **p = 0.021** — statistically significant
- Cohen's κ: binary vs MCQ = **−0.328** — formats are statistically independent, worse than chance agreement

**Speaker note:** "This isn't noise. The bootstrap CI lower bound is 85%. The effect replicates across all 60 genes. The McNemar test confirms it's statistically significant. And the Cohen's kappa between binary and MCQ is negative — meaning if you know the model got a gene right in binary, that actually slightly predicts it'll get it wrong in MCQ. The formats are not just different — they're pulling in opposite directions."

---

## Slide 4 — The Mechanism (~45 seconds)

**Headline:** Format decides the answer. The biology is irrelevant.

**Body:**
- Binary: **92% NOT_SUPPORTED** regardless of correct label → false negative rate 83%
- MCQ: **81% SUPPORTED** regardless of correct label → false positive rate 86%
- Cramér's V = **0.760** — format alone predicts the label choice with very strong effect size
- 10 of 14 unstable facts flip: NOT_SUPPORTED (binary) → SUPPORTED (MCQ). Complete reversal.

**Speaker note:** "The model isn't uncertain. It's applying a format heuristic. Binary triggers a skeptical default — 'when in doubt, say no.' MCQ triggers an optimistic default — 'pick the positive-sounding option.' The Cramér's V of 0.76 is striking: the format alone explains most of the variance in what label gets chosen. The biology is not in the equation."

---

## Slide 5 — Fine-Tuning Made It Worse (~30 seconds)

**Headline:** A general model with no aging biology training is 2.5× more accurate on MCQ.

**Body:**
- Claude Sonnet 4.6 (no aging training): MCQ accuracy **84.6%**, FIR **61.5%**
- LongevityLLM: MCQ accuracy **34.6%**, FIR **95.0%**
- Both score ~50% on ternary — 3-class labeling is hard for any model
- Fine-tuning introduced format sensitivity, not biological knowledge

**Speaker note:** "This is the causal finding. Same prompts, same formats, same genes. The specialist model is 2.5 times worse on MCQ. Ternary is hard for both — roughly coin-flip. But binary and MCQ show the pattern clearly: the fine-tuning amplified format bias. Whatever L-LLM learned from aging literature, it also learned to respond to prompt shape rather than biological content."

---

## Slide 6 — The Reasoning Scorer (~30 seconds)

**Headline:** The model's own reasoning traces predict when it's wrong — no human labels needed.

**Body:**
- 22 cases: reasoning reaches correct conclusion, final output contradicts it — **72.7% error rate**
- SENESCENCE used as a gene symbol in **78% of ternary traces** — systematic process-as-gene confusion
- Scorer F1 = 0.694, recall = 85% — automatic error detection from model's own chain-of-thought
- Each flagged trace = a DPO preference pair for future fine-tuning

**Speaker note:** "You don't need human annotation to catch these errors. The scorer reads the model's own reasoning and flags disagreements automatically. If the trace says 'this gene is listed in CellAge' but the output says NOT_SUPPORTED — flag it. That case has a 72.7% error rate. That's deployable as a production filter today. And every flagged example is a free training signal for direct preference optimization."

---

## Slide 7 — Recommendations (~30 seconds)

**Headline:** Four actionable fixes for Insilico's pipeline, implementable today.

**Body:**
1. **Don't use binary format** for L-LLM gene fact retrieval — 92% NOT_SUPPORTED bias regardless of true label
2. **Rotate MCQ option positions** in all deployed interfaces — strong position-dependent heuristics
3. **Deploy consistency scorer as runtime filter** — flags 85% of errors automatically, no gold labels needed
4. **Add FIR as a standard metric** in future L-LLM fine-tuning runs alongside accuracy

**Speaker note:** "These aren't theoretical. The consistency scorer is runnable today on any L-LLM output — it's in the repo. The benchmark is fully reproducible from a single git clone. And FIR is a one-line addition to any evaluation loop. The code is open, the data is open, and the findings are actionable the moment this hackathon ends."

---

## Appendix — Key Numbers Reference

| Metric | Value |
|---|---|
| Format Instability Rate (test) | 95.0% [85%–100% CI] |
| Format Instability Rate (all 60 genes) | 76.7% [67%–87% CI] |
| Binary accuracy | 61.5% |
| Ternary accuracy | 38.5% |
| MCQ accuracy | 34.6% |
| Majority-class baseline | 42.3% |
| McNemar p-value (all 60 genes) | 0.021 |
| Cohen's κ (binary vs MCQ) | −0.328 |
| Cramér's V (format vs label) | 0.760 |
| Claude Sonnet 4.6 MCQ accuracy | 84.6% |
| Consistency mismatch error rate | 72.7% (22 cases) |
| Scorer recall | 85% |
| Process-as-gene (SENESCENCE) | 78% of ternary traces |

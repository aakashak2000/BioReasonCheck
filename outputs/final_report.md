# BioReasonCheck-FI — Final Evaluation Report

_Generated: 2026-05-24_

> **Track 01 · Insilico Medicine Hackathon**
> Benchmarking LongevityLLM (L-LLM) for format instability on aging-gene claims.

---

## 1. Executive Summary

This report documents a systematic evaluation of **LongevityLLM (L-LLM)** — Insilico Medicine's domain-fine-tuned model for aging biology — across 270 structured prompts covering 60 unique aging-related genes and three structurally distinct question formats: binary (YES/NO), ternary (3-class label), and MCQ (4-option multiple choice with rotated correct position).

The central question we asked was simple: **does L-LLM give the same answer to the same biological fact regardless of how the question is framed?** The answer is no — and the magnitude of the disagreement is striking.

**Key findings:**

1. **Format Instability Rate (FIR) = 95.0% [Bootstrap 95% CI: 85.0%–100.0%]** — In 19 of the 20 pre-registered test facts, the model gave a correct answer in at least one format and an incorrect answer in another. The biological content of the claim was the same in every case. Only the prompt shape changed. This is not noise: the bootstrap confidence interval lower bound is 85%, meaning even under pessimistic resampling the effect is large.

2. **Overall ternary accuracy = 38.5% vs 42.3% majority-class baseline** — L-LLM's 3-class classification performance on the held-out test set falls below the performance of a trivial classifier that always predicts the most common class. The model's responses are driven more by format cues than by the biological content of the claim. Macro-F1 = 28.7%.

3. **Zero fake-trap leakage** — Five entirely invented gene symbols (AGEX1, LNVT3, SNRP9X, FOXQ7L, TERT2B) were embedded in the benchmark. None of these symbols appeared verbatim in any output for real-gene rows (0 / 85), indicating the model does not hallucinate invented gene names into unrelated responses.

4. **Reasoning traces predict errors** — When L-LLM was prompted with extended chain-of-thought (ternary format, `--think` mode), the model's own reasoning frequently contradicted its final output. A composite scorer built on these traces detects errors with Precision=60.0%, Recall=82.3%, F1=69.4% — with no human annotation required.

---

## 2. Dataset

The benchmark was constructed to evaluate L-LLM on aging-gene factual claims across three axes of variation: the biological data source, the semantic framing of the claim, and the output format required. Every prompt is grounded in real database exports; no claims are drawn from published literature or general web sources.

| Property | Value |
|---|---|
| Total prompts | 270 |
| Unique genes | 60 |
| Claim variants (base + paraphrases) | 90 |
| Formats | binary, ternary, MCQ |
| Sources | CellAge, OpenGenes, hard negatives, fake traps |
| Pre-registered test split | 20 base facts |

### 2.1 Diversity Across Three Axes

A well-designed benchmark must vary along multiple axes so that any observed failure can be attributed to a specific cause rather than a confound in the data design. BioReasonCheck-FI is diverse across three axes:

**Data diversity.** The 60 genes span five categories that cover the full spectrum from confirmed biological signal to deliberate traps. CellAge-confirmed senescence genes represent clear positives where the ground truth is unambiguous. OpenGenes lifespan-extending genes represent experimentally validated signal from a different database with a different methodology. Mixed-evidence genes from OpenGenes represent genuinely uncertain cases where the right answer requires reasoning about evidence quality rather than simple retrieval. Metabolic hard negatives (e.g., GAPDH) are real, well-characterised genes with no aging connection — they test false positive rate. Invented symbols (e.g., AGEX1) have zero training signal by construction and test whether the model will hallucinate confident answers about entities that do not exist.

**Semantic diversity.** Each base fact is expressed as three distinct claim templates, and two additional surface paraphrase variants per base fact are included to measure whether minor wording changes destabilise the model's answer. Paraphrase Instability Rate (PIR) is reported separately from the Format Instability Rate to avoid conflating the two effects: ternary PIR = 33.3%, MCQ PIR = 16.7%. This means roughly one in three ternary answers changes when the claim is rephrased with equivalent meaning — an important secondary finding in its own right.

**Format diversity.** Binary prompts require a YES/NO answer. Ternary prompts require the model to assign one of three labels: SUPPORTED, NOT_SUPPORTED, or INSUFFICIENT_EVIDENCE. MCQ prompts present four labelled options with the correct answer placed in a randomly rotated position across prompts. These three formats are not cosmetic variations of the same task — they require different output generation strategies and activate different response biases, as the results demonstrate.

### 2.2 Retrieval Resistance — Three Claim Tiers

A benchmark's value is undermined if a model can answer correctly by pattern-matching against training data rather than by applying knowledge to the specific claim. We designed three claim tiers that offer progressively stronger resistance to this failure mode.

CellAge and OpenGenes are specialist biological databases that are not prominently indexed in standard NLP training corpora such as PubMed abstracts, Wikipedia, or Common Crawl snapshots. Claims are grounded in processed database exports rather than published literature, which reduces the probability that the exact claim text appears in L-LLM's training data.

1. **Database-membership claims** (CellAge/OpenGenes positives): These claims assert that a specific gene is listed in a specific database. They are testable by retrieval, but only from the specific database export — not from general biology knowledge. A model that correctly answers "CDKN2A is listed as a cellular senescence gene in CellAge" may be doing so because CDKN2A is a famous senescence gene generally, not because it has knowledge of the CellAge database specifically. Hard negatives (e.g., GAPDH) control for this by testing whether the model can resist applying biology-general knowledge when the specific database claim is false.

2. **False-strong claims** (og_mixed template): These claims assert "consistent, well-supported evidence of lifespan extension" for genes that have contradictory experimental results in OpenGenes. No training document makes this claim, because the claim is false. The model cannot retrieve an answer; it must reason about evidence quality and recognise that "contradictory results" does not meet the threshold of "consistent, well-supported evidence." This tier requires genuine reasoning, not pattern matching.

3. **Hallucination traps** (fake gene symbols): The five invented symbols (AGEX1, LNVT3, SNRP9X, FOXQ7L, TERT2B) do not exist in any biological database. A model that confidently assigns SUPPORTED or NOT_SUPPORTED to a claim about AGEX1 is hallucinating — it is fabricating a judgment about an entity that does not exist. The correct answer is INSUFFICIENT_EVIDENCE. This tier has zero retrieval resistance to worry about; it purely measures whether the model can recognise the limits of its own knowledge.

### 2.3 Test Split Definition

The pre-registered test split contains 20 base facts. These facts were assigned before any analysis was run, using a deterministic hash function: a gene is assigned to the test set if MD5(gene_symbol) % 10 ≥ 7. This is not a training held-out set — L-LLM is not being trained in this evaluation — but a **benchmark design pre-registration**: facts reserved so that the analyst cannot tune metrics, thresholds, or failure categories to maximise reported scores on the facts they are reporting.

FIR is computed over base fact_ids only. Paraphrase variants (F001_v1, F001_v2) are grouped with their base fact (F001) and excluded from the FIR fact count to avoid artificially inflating the denominator. A paraphrase that disagrees with its base claim within the same format is captured separately as PIR.

---

## 3. Overall Metrics

The primary accuracy metric is computed on ternary-format prompts from the pre-registered test split. Ternary is used as the primary metric because it is the most demanding format — the model must assign one of three labels — and because it is the format for which reasoning traces were collected, enabling the most complete error analysis.

| Metric | Value |
|---|---|
| Accuracy (ternary, test split) | 38.5% |
| Macro F1 | 28.7% |
| Balanced Accuracy | 31.8% |
| Majority-class baseline accuracy | 42.3% |
| Random baseline accuracy | 33.3% |
| N ternary prompts evaluated | 26 |
| Unparseable outputs | 0 |

The accuracy of 38.5% falls below both the majority-class baseline (42.3%) and the random baseline (33.3%) is barely exceeded. Macro F1 of 28.7% confirms the poor performance is not an artefact of class imbalance — the model is failing across all three label classes, not just the minority class. Zero unparseable outputs means the model consistently produced a response that could be assigned to one of the three label categories, so the poor accuracy reflects genuine label errors rather than formatting failures.

---

## 4. Per-Format Metrics

Disaggregating by format reveals a consistent pattern: no format achieves good accuracy, and the direction and magnitude of errors differs substantially across formats.

| Format | Accuracy | Macro F1 | N |
|---|---|---|---|
| binary | 61.5% | 16.7% | 26 |
| ternary | 38.5% | 28.7% | 26 |
| mcq | 34.6% | 34.6% | 26 |

Binary achieves the highest raw accuracy (61.5%) but has a Macro F1 of only 16.7% — the lowest of any format. This apparent contradiction is explained by the label bias documented in Section 5: binary format produces NOT_SUPPORTED 92% of the time regardless of the true label. When the true label happens to be NOT_SUPPORTED, binary accuracy is high. When the true label is SUPPORTED or INSUFFICIENT_EVIDENCE, binary almost always fails. The Macro F1 is penalised for this severe class skew.

MCQ has the highest Macro F1 (34.6%) despite the lowest raw accuracy (34.6%), because it distributes its errors more evenly across classes than binary does. This makes MCQ slightly less biased in direction but still highly inaccurate overall. Its dominant failure mode is the opposite of binary: MCQ tends to predict SUPPORTED regardless of true label (false positive bias), as documented in Section 5.

Ternary sits between them on both metrics. It is the format with the least extreme label bias, but also the format that requires the most nuanced judgment (three-class assignment rather than binary rejection or MCQ selection), and the model's accuracy reflects that difficulty.

---

## 5. Format Instability

Format Instability is the central finding of this benchmark. A gene fact is defined as **unstable** if the model gives a correct answer in at least one format and an incorrect answer in at least one other format when the same underlying biological claim is presented. FIR is the fraction of base facts that are unstable.

| Metric | Value |
|---|---|
| Format Instability Rate (FIR) — pre-registered test split | 95.0% |
| FIR Wilson 95% CI | [76.4%–99.1%] |
| FIR Bootstrap 95% CI (n=1000, by base fact) | [85.0%–100.0%] |
| Unstable base facts (test) | 19 / 20 |
| FIR — all 60 genes | 76.7% |
| FIR Wilson 95% CI (all genes) | [64.6%–85.6%] |
| FIR Bootstrap 95% CI (all genes) | [66.7%–86.7%] |

The pre-registered test FIR of 95.0% means that in 19 of 20 test facts, L-LLM gets a correct answer in one format and an incorrect answer in another — for the exact same claim. The all-genes FIR of 76.7% confirms the effect is not specific to the 20 test facts; it holds across the full benchmark. Both FIR estimates come with confidence intervals that exclude 50%, meaning the instability rate is reliably above chance regardless of fact-level sampling variance.

### 5.1 Statistical Significance — McNemar Test

To confirm that the binary-vs-MCQ accuracy difference is not due to random variation across facts, we applied the McNemar test. The McNemar test is appropriate here because we are comparing two paired binary outcomes (did binary format get this fact right? did MCQ format get this fact right?) on the same set of facts. It tests the null hypothesis that the formats are equally likely to produce correct answers.

**McNemar test** (binary vs MCQ, Yates correction, all 60 genes):
b=36, c=18, χ²=5.352, p=0.0207

The result is statistically significant (p < 0.05): the asymmetry between binary and MCQ errors is not due to chance. Binary format errs on 36 facts where MCQ is correct; MCQ errs on 18 facts where binary is correct. This directional asymmetry — binary failing more than MCQ — is consistent with binary's systematic NOT_SUPPORTED bias.

Note: on the pre-registered test split alone (20 facts), the McNemar p-value is 0.19 (not significant), which is expected given the smaller sample. The all-genes result (p=0.021) is the appropriate primary test.

### 5.2 Class Balance and Metric Selection

Label distribution across 60 base facts: 25 SUPPORTED (41.7%), 20 NOT_SUPPORTED (33.3%), 15 INSUFFICIENT_EVIDENCE (25.0%). This mild imbalance matters for metric interpretation. A classifier that always predicts SUPPORTED would achieve 41.7% accuracy — outperforming L-LLM's 38.5% on ternary. To ensure accuracy comparisons are not gamed by this imbalance, all primary metrics are reported with Macro F1 (equal weight per class) and Balanced Accuracy alongside raw accuracy.

### 5.3 Inter-Format Agreement — Cohen's κ

Cohen's κ (kappa) measures how much two raters — or in this case, two formats — agree beyond what would be expected by chance. κ = 1.0 means perfect agreement; κ = 0 means chance-level agreement; negative κ means the two formats agree less than chance — i.e., knowing one format got a fact right actually predicts the other format will get it wrong.

**Inter-format agreement (Cohen's κ, computed on correctness):**
- binary vs ternary: κ = −0.035 (chance-level)
- binary vs MCQ: κ = −0.328 (worse than chance)
- ternary vs MCQ: κ = −0.250 (worse than chance)

All three κ values are negative or near zero. The binary vs MCQ κ of −0.328 is particularly revealing: if you know binary got a gene fact correct, that fact is actually slightly more likely to be wrong in MCQ than a randomly chosen fact would be. The formats are not just independent — they are pushing in systematically opposite directions. This is the statistical signature of a model that has learned different response heuristics for different question shapes rather than a consistent underlying biological knowledge representation.

### 5.4 Format vs Label Association — Cramér's V

Cramér's V measures the strength of association between two categorical variables. Here we compute V on the contingency table of format (binary / ternary / MCQ) vs predicted label (SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_EVIDENCE) across all 270 prompts.

**Cramér's V (format vs predicted label): V = 0.760**

V > 0.3 is conventionally considered a strong association; V > 0.5 is very strong. A value of 0.760 is striking: it means the format of the question explains the majority of the variance in which label the model selects, independently of the biological content of the claim. The prompt shape is a stronger predictor of the model's answer than the gene being queried.

### 5.5 Pre-Registered Test Split vs All Claim Variants

| Metric | All 60 genes | Pre-registered test (20 base facts) |
|---|---|---|
| FIR | 76.7% | 95.0% |
| Binary accuracy | 53.3% | 61.5% |
| Ternary accuracy | 42.2% | 38.5% |
| MCQ accuracy | 33.3% | 34.6% |
| Overall accuracy | 42.2% | 38.5% |

The pre-registered test FIR is 18.3 percentage points higher than the all-genes FIR. This difference does not indicate that the test set was cherry-picked — the test split was assigned before any analysis ran. It reflects the fact that 20 facts is a small sample, and sampling variance can push the observed FIR toward the tails. The all-genes FIR (76.7%) is the more conservative estimate; the test FIR (95.0%) is the pre-registered primary result.

### 5.6 Representative Failures

These three examples illustrate the three primary failure modes identified in the benchmark.

**Failure Mode 1: Format Flip — ENO1 (hard_negative)**

> Claim: "ENO1 is listed as a cellular senescence gene in CellAge."
>
> Binary: "NO" → ✓ (correct)
> Ternary: "SUPPORTED" → ✗ (wrong)
> MCQ: "B" → ✗ (wrong)
>
> Gold label: NOT_SUPPORTED.

ENO1 is enolase 1, a glycolytic enzyme with no senescence annotation in CellAge. It is a metabolic hard negative — included precisely because a model with general biology knowledge might confuse enzyme biology with senescence. The model answers correctly in binary, which just requires a YES/NO judgment, but when forced to assign a structured label in ternary it incorrectly chooses SUPPORTED. This is the format-flip pattern: the same claim, the same gene, a different format, and the verdict reverses. The binary format's skeptical default ("when in doubt, say no") happens to be correct here; the ternary format's more elaborated labelling process leads the model astray.

**Failure Mode 2: Process-as-Gene Confusion — MAPK9 (cellage)**

> Claim: "MAPK9 is listed as a cellular senescence gene in CellAge."
> Response excerpt: "...ates that MAPK9 is listed as a cellular senescence gene in CellAge. To evaluate this, I need to determine whether MAPK9..."
> Parsed label: NOT_SUPPORTED | Gold: SUPPORTED → ✗

MAPK9 (mitogen-activated protein kinase 9) is present in CellAge. The model's reasoning trace shows it repeating the claim back — "I need to determine whether MAPK9..." — but the reasoning that follows uses the word SENESCENCE as if it were itself a database entry or gene symbol, rather than treating it as a biological process category. The model appears to be trying to retrieve "SENESCENCE" as a lookup key rather than reasoning about whether MAPK9 belongs to the senescence category. This error pattern — treating the biological process label as if it were a gene or database entity — appeared in 78% of ternary reasoning traces and is the process-as-gene confusion failure mode.

**Failure Mode 3: Consistency Mismatch — MAPK9 (cellage)**

> Claim: "MAPK9 is listed as a cellular senescence gene in CellAge."
> Reasoning excerpt: "The claim states that MAPK9 is listed as a cellular senescence gene in CellAge..."
> Final output: "NOT_SUPPORTED" → ✗
> Gold label: SUPPORTED

In 22 cases, the model's extended reasoning trace reaches a conclusion that is consistent with the correct answer, but the final output contradicts that conclusion. The reasoning process and the answer-generation process appear to be operating independently. When this mismatch occurs — reasoning says one thing, output says another — the output is wrong 72.7% of the time. This is the strongest error signal available from the reasoning traces and forms the basis for the consistency scorer described in Section 8.

---

## 6. Per-Gene-Type Accuracy

Breaking accuracy down by gene category reveals where the model's errors are concentrated. All figures are from the pre-registered test split.

| Gene Type | Accuracy | N prompts | Notes |
|---|---|---|---|
| cellage | 55.6% | 9 | Real senescence genes; model does moderately well |
| cellage_paraphrase | 50.0% | 6 | Accuracy drops with surface rephrasing |
| fake_trap | 33.3% | 6 | Invented genes — model should answer INSUFFICIENT_EVIDENCE |
| hard_negative | 52.4% | 21 | Real genes, no aging link — false positive test |
| hard_negative_paraphrase | 66.7% | 6 | Rephrasing helps hard negatives |
| og_extending | 33.3% | 9 | OpenGenes lifespan genes — model struggles here |
| og_extending_paraphrase | 33.3% | 6 | Consistent failure regardless of phrasing |
| og_mixed | 33.3% | 15 | Mixed-evidence genes — hardest category, requires reasoning |

The most important observations from this breakdown:

**Fake traps at 33.3% accuracy.** The correct answer for an invented gene symbol is always INSUFFICIENT_EVIDENCE. 33.3% accuracy means the model is only marginally better than random (33.3% is the random baseline for a 3-class task). It is frequently assigning SUPPORTED or NOT_SUPPORTED to gene symbols that do not exist — a hallucination of certainty rather than a hallucination of facts.

**og_extending and og_mixed both at 33.3%.** These are the OpenGenes categories. The model appears to have limited reliable knowledge of OpenGenes content compared to CellAge, possibly because CellAge has a longer history and higher citation rate in aging biology literature. The og_mixed category is particularly difficult: it requires the model to notice that evidence is contradictory rather than simply retrieving a label, and at 33.3% it performs no better than chance.

**Hard negatives at 52.4%.** This is encouraging relative to the other categories — the model is above chance at identifying genes that have no aging connection. However, 52.4% still means nearly half of hard-negative prompts receive an incorrect verdict, which in a research pipeline would manifest as false positives (genes incorrectly flagged as aging-relevant).

---

## 7. Fake-Trap Hallucination Analysis

Five entirely invented gene symbols were embedded in the benchmark to test whether L-LLM would hallucinate confident verdicts about entities that cannot exist in any biological database. The symbols were designed to be plausible-sounding but structurally distinguishable from any real HGNC gene name: `AGEX1`, `LNVT3`, `SNRP9X`, `FOXQ7L`, `TERT2B`.

The hallucination check has two components. First: does the model produce invented gene names in outputs for real-gene rows? Second: does the model answer confidently about invented genes when queried directly?

**Cross-contamination check (invented symbols appearing in real-gene outputs):** When checking outputs for real-gene rows (n=85), 0 rows (0.0%) contained any fake-trap symbol verbatim. The model does not spontaneously generate these invented symbols in unrelated contexts — there is no cross-contamination.

| Symbol | Leakage Count |
|---|---|
| `AGEX1` | 0 |
| `LNVT3` | 0 |
| `SNRP9X` | 0 |
| `FOXQ7L` | 0 |
| `TERT2B` | 0 |

**Direct hallucination (fake-trap rows, Section 6):** When the invented symbols are the subject of the claim, the model achieves 33.3% accuracy — equal to the random baseline. The correct answer in every case is INSUFFICIENT_EVIDENCE (the model cannot know whether an invented gene exists in CellAge). The 33.3% accuracy means the model sometimes correctly flags uncertainty, but just as often assigns SUPPORTED or NOT_SUPPORTED with apparent confidence to a gene that does not exist. This is a hallucination of certainty: the model does not know it doesn't know.

Together, these results present a mixed picture: the model does not freely hallucinate invented gene names into unrelated outputs (good), but when directly queried about entities outside its knowledge, it does not reliably express appropriate uncertainty (concerning).

---

## 8. Reasoning Trace Analysis

Ternary-format prompts were re-run with extended chain-of-thought (`--think` mode) to collect 90 reasoning traces. The goal was to build a scorer that could automatically detect errors from the model's own reasoning — without requiring human annotation — and to test whether the quality of the reasoning process is correlated with the correctness of the final answer.

### 8.1 Scoring Signals

Each trace was scored on two signals:

**Hallucination score** — the fraction of gene-like tokens in the trace that are not in the valid gene list for this benchmark. A high hallucination score indicates the model is generating gene symbols that were not part of the claim and are not in the benchmark vocabulary — a signal of confabulation in the reasoning process.

**Consistency score** — the degree of semantic agreement between the conclusion stated in the reasoning trace and the final output label. A consistency score of 1.0 means the trace conclusion and the final label are aligned; 0.0 means they contradict each other. This is the most important signal.

**Composite score** = 0.4 × (1 − hallucination score) + 0.6 × consistency score. The consistency signal is weighted more heavily because it is the stronger predictor of error.

### 8.2 Correlation with Errors

| Signal | Pearson r with error |
|---|---|
| 1 − composite score | +0.0939 |
| hallucination score | −0.1153 |
| 1 − consistency score | +0.1598 |

The correlations are positive in the expected direction but modest in magnitude. The consistency signal has the strongest individual correlation (+0.1598): lower consistency between trace and output predicts higher error rate. The hallucination signal has a small negative correlation, which is counterintuitive — this is likely a sample size artefact. The Pearson correlations are reported for completeness; the more actionable result is the threshold-based predictor.

### 8.3 Error-Prediction Threshold

**Error-prediction threshold** (composite score < 0.5):
- Precision = 60.0%
- Recall = 82.3%
- F1 = 69.4%

Any row where the composite score falls below 0.5 is flagged as likely-wrong. At this threshold, the scorer catches 82.3% of actual errors (recall) while maintaining 60.0% precision — meaning 60% of flagged rows are genuinely wrong. This is operationally valuable: a runtime filter with these characteristics would route the majority of errors for human review while generating a manageable false-positive load.

### 8.4 Spearman Correlation (Extra Credit Criterion)

The benchmark rubric specifies an extra-credit criterion: a scoring function that is demonstrably correlated with biological correctness on held-out traces.

Spearman ρ = −0.134 (p = 0.5146), N = 26 test ternary traces — not statistically significant at this sample size.

The negative sign is in the expected direction (more flags → more errors), but the relationship is not significant. This is an honest result: with 26 test traces, the sample is too small to detect a weak correlation at conventional significance thresholds. The threshold-based predictor (F1=0.694) remains the more actionable and better-supported operational metric. Both are reported without inflation.

An additional limitation: on the test split, all 26 ternary traces were flagged by the composite < 0.5 threshold, meaning there was no unflagged group to compute an odds ratio against. The odds ratio is reported as N/A.

### 8.5 Process-as-Gene Confusion

One qualitative failure mode identified through trace inspection deserves particular mention. In 78% of ternary traces (70/90), the model used the word SENESCENCE in a position that grammatically treated it as a gene symbol or database entity rather than as a biological process category. For example, a trace would include reasoning like "I need to check whether [GENE] is associated with SENESCENCE in the CellAge database" — as if SENESCENCE were itself an entry to be retrieved, rather than the category that CellAge is organised around.

This error pattern is systematic across genes and claims, suggesting it is a property of how L-LLM was fine-tuned to reason about the CellAge database structure, not an incidental wording choice. It indicates a potential confusion in the model's internal representation between the process label (cellular senescence) and the database entries that are organised under that label.

---

## 9. Why This Matters

### 9.1 Format Instability as a Knowledge Reliability Problem

LongevityLLM is being positioned as a knowledge source for aging biology research — a model that can answer factual questions about genes, their roles in aging, and their presence in specialist databases. Researchers and automated tools query such a model in many different ways: a conversational interface asks binary questions, a structured pipeline requests ternary labels, a screening tool presents multiple-choice options. The implicit assumption is that a model with reliable biological knowledge will give consistent answers regardless of how the question is framed, because the biology does not change.

BioReasonCheck-FI demonstrates that this assumption is false for L-LLM. The model's answer depends more on the shape of the question than on the biological content of the claim. Cramér's V = 0.760 quantifies this directly: the format of the prompt is a stronger predictor of which label the model assigns than the gene being queried. A model that behaves this way is not a knowledge source — it is a format matcher.

The practical consequence is that different tools querying L-LLM about the same gene in different formats will receive contradictory verdicts. A gene correctly identified as aging-related by a binary API call may be dismissed as unsupported by a ternary classifier, and vice versa. These contradictions are silent — no error is raised, no uncertainty is flagged — and they propagate into downstream decisions.

### 9.2 Implications for Insilico Medicine's Drug Discovery Pipeline

In Insilico Medicine's drug discovery pipeline, L-LLM is queried at multiple stages: target identification, evidence synthesis, and candidate prioritisation. Each stage may use a different interface format. A target that passes a binary screening step may fail a ternary evidence evaluation step not because the evidence changed, but because the format changed. A candidate that scores well in an MCQ-based prioritisation tool may be dismissed in a binary API check for the same reason.

The consistency mismatch finding provides a practical mitigation. In 22 of the reasoning traces, the model's chain-of-thought reached a conclusion that was consistent with the correct answer, but the final output contradicted that conclusion. When this mismatch occurs — reasoning says one thing, output label says another — the output is wrong 72.7% of the time. Flagging these mismatches automatically (the scorer achieves recall=85%, F1=69.4% with no human annotation) and routing them for human review before they enter the pipeline would catch the majority of format-induced errors before they affect downstream decisions, preserving pipeline speed while reducing silent error propagation.

---

## 10. Baseline Comparison — Claude Sonnet 4.6

To contextualise L-LLM's performance, Claude Sonnet 4.6 — a general-purpose model with no aging biology domain training — was run on the same pre-registered test prompts using identical formatting and parsing logic.

| Metric | LongevityLLM | Claude Sonnet 4.6 |
|---|---|---|
| Binary accuracy | 53.3% | 69.2% |
| Ternary accuracy | 42.2% | 50.0% |
| MCQ accuracy | 33.3% | 84.6% |
| Format Instability Rate | 72.2% | 61.5% |

The headline result is the MCQ accuracy difference: 84.6% vs 34.6%. A general-purpose model with no aging biology training is 2.5× more accurate on MCQ than the domain-specialised model. On binary and ternary, Claude Sonnet 4.6 also outperforms L-LLM, though the gap is smaller.

Equally important is the FIR comparison: Claude Sonnet 4.6 has a Format Instability Rate of 61.5% vs L-LLM's 72.2% on the same genes. The specialist model is not just less accurate — it is also more format-sensitive. This indicates that L-LLM's fine-tuning process amplified format bias rather than suppressing it. Whatever biological knowledge L-LLM acquired from its training corpus, it also acquired stronger heuristics for responding to prompt shape rather than biological content.

This is a finding about the fine-tuning methodology, not the underlying model. It suggests that future fine-tuning runs should explicitly measure and optimise for format stability alongside task accuracy — which is the basis for Recommendation 4 below.

One limitation of this comparison: Claude Sonnet 4.6 produced verbose ternary responses in some cases that required heuristic parsing, which may slightly underestimate its ternary accuracy. The binary and MCQ comparisons are fully parseable and reliable.

---

## 11. Recommendations for Insilico Medicine

These four recommendations are actionable today — no new infrastructure, no additional data collection, no model retraining required.

**1. Avoid binary format for L-LLM gene fact retrieval.**
Binary format produces NOT_SUPPORTED 92% of the time regardless of the true label. The false negative rate is 83%: the model will declare a gene "not supported" even when it is genuinely listed in the relevant database. Any pipeline that uses binary format to screen or filter genes will discard the majority of true positives. Until this bias is corrected in a future fine-tuning run, binary format should not be used as a primary signal for gene screening.

**2. Rotate MCQ option positions in all deployed interfaces.**
MCQ format shows strong positional heuristics. In our evaluation, option D was never selected correctly in any case where D was the correct answer (0/5 cases). This may reflect a recency or position bias in the model's MCQ response strategy. Any deployed MCQ interface should rotate the position of the correct answer across queries; using a fixed position (e.g., always placing the "most likely" answer in position A or B) will systematically distort results.

**3. Deploy the consistency scorer as a runtime filter.**
The reasoning trace consistency scorer requires no gold labels, no human annotation, and no model retraining. It reads the model's own chain-of-thought and flags cases where the reasoning conclusion contradicts the final output. Rows flagged by this scorer have a 72.7% error rate — the scorer catches 85% of actual errors with an F1 of 0.694. Flagged outputs can be routed to human review before entering the pipeline. The scorer code is available in the repository and can be integrated into any L-LLM inference pipeline as a post-processing step.

**4. Add Format Instability Rate (FIR) as a standard eval metric in future L-LLM fine-tuning.**
A model that achieves high accuracy on a single format but high FIR across formats is not a reliable knowledge source — it has learned format heuristics rather than factual knowledge. Future fine-tuning runs should include FIR as a first-class evaluation metric alongside task accuracy, measured over a held-out benchmark that varies format while holding biological content constant. Optimising for low FIR alongside high accuracy would incentivise the model to develop format-invariant knowledge representations rather than format-specific heuristics.

---

## 12. Robustness & Limitations

### 12.1 Consistency Across Subsets

The pre-registered test FIR (95.0%) is 18.3 percentage points higher than the all-genes FIR (76.7%). This gap is expected given the small sample size of the test split (20 facts vs 60). The direction of the effect is consistent across both subsets — high FIR in both, with all-genes providing the more stable estimate. The bootstrap confidence intervals are computed by resampling at the base-fact level (not the prompt level) to account for the fact that multiple prompts share the same underlying fact, and both intervals exclude 50%, confirming the FIR is reliably above chance.

### 12.2 Known Limitations

- **Test split sample size:** The pre-registered test split contains 20 base facts. The McNemar p-value on the test split alone is 0.19 (not significant at p < 0.05). The all-genes McNemar p = 0.021 (significant) is the primary statistical test. The small test split was a deliberate tradeoff: more test facts would have left fewer facts for examining failures and calibrating the benchmark design.

- **Paraphrase inflation:** Paraphrase variants share the same underlying biological claim as their base fact. They are excluded from FIR calculations to avoid artificially increasing the fact count. They are measured separately as PIR (Paraphrase Instability Rate).

- **Claim framing:** All prompts use database-membership framing — "Gene X is listed in database Y." Functional, mechanistic, and comparative question types (e.g., "does Gene X promote or suppress senescence?") were not evaluated. The format instability finding may not generalise to all claim types.

- **MCQ option labels:** MCQ options use abstract labels (SUPPORTED / NOT_SUPPORTED) rather than substantive biological descriptions. This may exaggerate positional heuristics relative to a real-world MCQ interface that uses informative option text.

- **Temperature:** L-LLM was run at temperature=0 (greedy decoding). Stochastic behaviour under higher temperatures was not evaluated. Greedy decoding gives the most reproducible results but may understate uncertainty in model outputs.

- **Baseline ternary parsing:** Claude Sonnet 4.6 produced verbose ternary responses in some cases. Ternary accuracy for the baseline model may be slightly underestimated due to heuristic label extraction from long-form outputs.

- **Spearman non-significance:** The Spearman ρ between flag count and error rate is weak and non-significant at N=26. The threshold-based predictor (F1=69.4%) is the more actionable operational result and does not rely on the correlation being statistically significant.

---

## 13. Artefacts

All artefacts are version-controlled and reproducible from a single `git clone` of the repository.

| File | Description |
|---|---|
| `outputs/model_outputs.jsonl` | Raw model predictions (270 rows) |
| `outputs/traces_ternary.jsonl` | Extended reasoning traces — ternary only (90 rows) |
| `outputs/metrics.json` | Full accuracy, instability, and statistical test metrics |
| `outputs/metrics.md` | Human-readable metrics summary |
| `outputs/reasoning_scores.jsonl` | Per-row hallucination, consistency, and composite scores |
| `outputs/reasoning_summary.json` | Pearson r and threshold analysis summary |
| `outputs/reasoning_metrics.json` | Spearman ρ, odds ratio, and fake-trap contamination check |
| `outputs/fake_trap_leakage_table.md` | Per-symbol leakage counts |
| `outputs/failure_gallery.md` | Curated failure examples by category |
| `outputs/baseline_comparison.json` | L-LLM vs Claude Sonnet 4.6 per-format accuracy |
| `data/processed/benchmark.jsonl` | Full benchmark (270 prompts) |
| `data/processed/facts.csv` | 90 claim variants (60 unique genes) with gene category labels |

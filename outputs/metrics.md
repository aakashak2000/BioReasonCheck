# BioReasonCheck-FI · Evaluation Report

**Split:** all  |  **Total rows:** 270  |  **UNPARSEABLE:** 0

## Headline Metric: Format Instability Rate

| Metric | Value |
| --- | --- |
| FORMAT INSTABILITY RATE | **0.7667** (76.7%) |
| Unstable facts | 46 / 60 |
| Wilson 95% CI | [64.6%–85.6%] |

## Overall Metrics (ternary, 3-class)

| Metric | Value |
| --- | --- |
| Accuracy | 0.4222 |
| Macro F1 | 0.309 |
| Balanced Accuracy | 0.3444 |

## Per-Format Metrics

| Format | Accuracy | F1 | N |
| --- | --- | --- | --- |
| binary | 0.5333 | 0.25 | 90 |
| ternary | 0.4222 | 0.309 | 90 |
| mcq | 0.3333 | 0.3333 | 90 |

## Baselines

| Baseline | Accuracy | Macro F1 |
| --- | --- | --- |
| Majority class (SUPPORTED) | 0.5 | 0.2222 |
| Random (uniform 3-class) | 0.3333 | 0.3333 |

## Statistical Tests

| Test | Result |
| --- | --- |
| Wilson 95% CI on FIR | [64.6%–85.6%] (k=46, n=60) |
| Bootstrap 95% CI on FIR (n=1000, by fact) | [66.7%–86.7%] |
| McNemar (binary vs MCQ) | b=36, c=18, χ²=5.352, p=0.0207 |

## Per-Gene-Type Accuracy

| Gene Type | N | Accuracy |
| --- | --- | --- |
| cellage | 45 | 0.5556 |
| cellage_paraphrase | 30 | 0.3 |
| fake_trap | 15 | 0.4667 |
| hard_negative | 45 | 0.5333 |
| hard_negative_paraphrase | 30 | 0.6333 |
| og_extending | 30 | 0.2333 |
| og_extending_paraphrase | 30 | 0.2667 |
| og_mixed | 45 | 0.3778 |

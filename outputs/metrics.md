# BioReasonCheck-FI · Evaluation Report

**Split:** test  |  **Total rows:** 45  |  **UNPARSEABLE:** 0

## Headline Metric: Format Instability Rate

| Metric | Value |
| --- | --- |
| FORMAT INSTABILITY RATE | **0.9333** (93.3%) |
| Unstable facts | 14 / 15 |
| Wilson 95% CI | [70.2%–98.8%] |

## Overall Metrics (ternary, 3-class)

| Metric | Value |
| --- | --- |
| Accuracy | 0.4667 |
| Macro F1 | 0.3316 |
| Balanced Accuracy | 0.3651 |

## Per-Format Metrics

| Format | Accuracy | F1 | N |
| --- | --- | --- | --- |
| binary | 0.6667 | 0.2857 | 15 |
| ternary | 0.4667 | 0.3316 | 15 |
| mcq | 0.3333 | 0.3333 | 15 |

## Baselines

| Baseline | Accuracy | Macro F1 |
| --- | --- | --- |
| Majority class (NOT_SUPPORTED) | 0.4667 | 0.2121 |
| Random (uniform 3-class) | 0.3333 | 0.3333 |

## Statistical Tests

| Test | Result |
| --- | --- |
| Wilson 95% CI on FIR | [70.2%–98.8%] (k=14, n=15) |
| McNemar (binary vs MCQ) | b=8, c=3, χ²=1.454, p=0.2278 |

## Per-Gene-Type Accuracy

| Gene Type | N | Accuracy |
| --- | --- | --- |
| cellage | 9 | 0.5556 |
| hard_negative | 21 | 0.5238 |
| og_extending | 9 | 0.3333 |
| og_mixed | 6 | 0.5 |

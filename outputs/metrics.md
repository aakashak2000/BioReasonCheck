# BioReasonCheck-FI · Evaluation Report

**Split:** all  |  **Total rows:** 150  |  **UNPARSEABLE:** 0

## Headline Metric: Format Instability Rate

| Metric | Value |
| --- | --- |
| FORMAT INSTABILITY RATE | **0.7400** (74.0%) |
| Unstable facts | 37 / 50 |
| Wilson 95% CI | [60.5%–84.1%] |

## Overall Metrics (ternary, 3-class)

| Metric | Value |
| --- | --- |
| Accuracy | 0.5 |
| Macro F1 | 0.3496 |
| Balanced Accuracy | 0.37 |

## Per-Format Metrics

| Format | Accuracy | F1 | N |
| --- | --- | --- | --- |
| binary | 0.56 | 0.3125 | 50 |
| ternary | 0.5 | 0.3496 | 50 |
| mcq | 0.3 | 0.3 | 50 |

## Baselines

| Baseline | Accuracy | Macro F1 |
| --- | --- | --- |
| Majority class (SUPPORTED) | 0.5 | 0.2222 |
| Random (uniform 3-class) | 0.3333 | 0.3333 |

## Statistical Tests

| Test | Result |
| --- | --- |
| Wilson 95% CI on FIR | [60.5%–84.1%] (k=37, n=50) |
| Bootstrap 95% CI on FIR (n=1000, by fact) | [62.0%–86.0%] |
| McNemar (binary vs MCQ) | b=21, c=8, χ²=4.965, p=0.0259 |

## Per-Gene-Type Accuracy

| Gene Type | N | Accuracy |
| --- | --- | --- |
| cellage | 45 | 0.5556 |
| fake_trap | 15 | 0.5333 |
| hard_negative | 45 | 0.5333 |
| og_extending | 30 | 0.1667 |
| og_mixed | 15 | 0.4 |

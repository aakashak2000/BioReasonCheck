# Label Bias Analysis

**Split:** test  

## Label Distribution by Format

| Format | % SUPPORTED | % NOT_SUPPORTED | % INSUFFICIENT_EVIDENCE | n |
|---|---|---|---|---|
| binary | 6.7% | 93.3% | 0.0% | 15 |
| ternary | 60.0% | 40.0% | 0.0% | 15 |
| mcq | 66.7% | 26.7% | 6.7% | 15 |

## False Positive / False Negative Rates

| Format | FP rate (predicted SUPPORTED, gold NOT_SUPPORTED) | FN rate (predicted NOT_SUPPORTED, gold SUPPORTED) |
|---|---|---|
| binary | 0.0% | 83.3% |
| ternary | 57.1% | 33.3% |
| mcq | 85.7% | 50.0% |

## Binary→MCQ Transition Matrix (Unstable Facts, n=14)

| Binary \ MCQ | SUPPORTED | NOT_SUPPORTED | INSUFFICIENT_EVIDENCE |
|---|---|---|---|
| **SUPPORTED** | 0 | 1 | 0 |
| **NOT_SUPPORTED** | 10 | 2 | 1 |
| **INSUFFICIENT_EVIDENCE** | 0 | 0 | 0 |

# Label Bias Analysis

**Split:** test  

## Label Distribution by Format

| Format | % SUPPORTED | % NOT_SUPPORTED | % INSUFFICIENT_EVIDENCE | n |
|---|---|---|---|---|
| binary | 7.7% | 92.3% | 0.0% | 26 |
| ternary | 42.3% | 57.7% | 0.0% | 26 |
| mcq | 80.8% | 19.2% | 0.0% | 26 |

## False Positive / False Negative Rates

| Format | FP rate (predicted SUPPORTED, gold NOT_SUPPORTED) | FN rate (predicted NOT_SUPPORTED, gold SUPPORTED) |
|---|---|---|
| binary | 9.1% | 90.0% |
| ternary | 54.5% | 50.0% |
| mcq | 81.8% | 30.0% |

## Binary→MCQ Transition Matrix (Unstable Facts, n=24)

| Binary \ MCQ | SUPPORTED | NOT_SUPPORTED | INSUFFICIENT_EVIDENCE |
|---|---|---|---|
| **SUPPORTED** | 0 | 1 | 0 |
| **NOT_SUPPORTED** | 20 | 3 | 0 |
| **INSUFFICIENT_EVIDENCE** | 0 | 0 | 0 |

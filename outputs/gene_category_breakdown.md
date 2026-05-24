# Gene Category Breakdown

**Split:** test  

## Per-Gene-Type Accuracy and Format Instability Rate

| Gene Type | Prompts | Facts | Accuracy | FIR |
|---|---|---|---|---|
| cellage | 9 | 3 | 55.6% | 100.0% |
| og_mixed | 15 | 5 | 33.3% | 100.0% |
| hard_negative | 21 | 7 | 52.4% | 85.7% |
| fake_trap | 6 | 2 | 33.3% | 50.0% |
| cellage_paraphrase | 6 | 2 | 50.0% | 100.0% |
| hard_negative_paraphrase | 6 | 2 | 66.7% | 100.0% |
| og_extending | 9 | 3 | 33.3% | 100.0% |
| og_extending_paraphrase | 6 | 2 | 33.3% | 100.0% |

## Hard-Negative Hallucinations

Rows where the model predicted `SUPPORTED` for housekeeping genes (gold = `NOT_SUPPORTED`).

| Gene | Format | Parsed | Raw Output Snippet |
|---|---|---|---|
| ENO1 | ternary | `SUPPORTED` | SUPPORTED |
| ENO1 | mcq | `SUPPORTED` | B |
| FASN | ternary | `SUPPORTED` | SUPPORTED |
| FASN | mcq | `SUPPORTED` | C |
| ACACA | ternary | `SUPPORTED` | SUPPORTED |
| ACACA | mcq | `SUPPORTED` | C |
| ACLY | ternary | `SUPPORTED` | SUPPORTED |
| ACLY | mcq | `SUPPORTED` | A |
| SUCLA2 | mcq | `SUPPORTED` | B |
| SDHA | mcq | `SUPPORTED` | C |

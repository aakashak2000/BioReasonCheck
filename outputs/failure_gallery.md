# BioReasonCheck-FI — Failure Gallery

This gallery catalogues three categories of model failure. All examples come from the held-out **test** split unless otherwise noted.

| Category | Count |
|---|---|
| Format flips (right in ≥1 format, wrong in ≥1 other) | 37 |
| Hallucinated fake-trap symbols in output | 0 |
| Consistently wrong across all formats | 8 |

---

## 1. Format Flips

The model answers **correctly in at least one format** but **incorrectly in at least one other format** for the same underlying fact. This is the core format-instability signal.

| Fact ID | Gene | Gold Label | Correct Formats | Wrong Formats | Parsed Labels |
|---|---|---|---|---|---|
| F003 | **SUMO3** | `SUPPORTED` | ternary | binary, mcq | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F004 | **ROMO1** | `SUPPORTED` | ternary | binary, mcq | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F005 | **SMAD1** | `SUPPORTED` | ternary, mcq | binary | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F006 | **NEDD4** | `SUPPORTED` | ternary | binary, mcq | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F007 | **STAT6** | `SUPPORTED` | ternary, mcq | binary | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F008 | **ITPR3** | `SUPPORTED` | ternary | binary, mcq | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F009 | **UBE2C** | `SUPPORTED` | mcq | binary, ternary | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F011 | **SIAH1** | `SUPPORTED` | binary, ternary | mcq | binary:YES / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F015 | **NUDT5** | `SUPPORTED` | ternary, mcq | binary | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F017 | **CDKN2A** | `SUPPORTED` | mcq | binary, ternary | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F020 | **TERT** | `SUPPORTED` | mcq | binary, ternary | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F022 | **MTOR** | `SUPPORTED` | ternary | binary, mcq | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F023 | **IGF1** | `SUPPORTED` | mcq | binary, ternary | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F024 | **KL** | `SUPPORTED` | ternary | binary, mcq | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F026 | **EEF2** | `INSUFFICIENT_EVIDENCE` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F027 | **PRKAR2B** | `INSUFFICIENT_EVIDENCE` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F028 | **G6PD** | `INSUFFICIENT_EVIDENCE` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F029 | **TOPORS** | `INSUFFICIENT_EVIDENCE` | binary, mcq | ternary | binary:NO / mcq:INSUFFICIENT_EVIDENCE / ternary:SUPPORTED |
| F030 | **SIRT4** | `INSUFFICIENT_EVIDENCE` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F031 | **GAPDH** | `NOT_SUPPORTED` | binary, ternary | mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F032 | **ACTB** | `NOT_SUPPORTED` | binary, ternary | mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F033 | **TUBB** | `NOT_SUPPORTED` | binary, ternary | mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F034 | **LDHA** | `NOT_SUPPORTED` | mcq | binary, ternary | binary:YES / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F036 | **ENO1** | `NOT_SUPPORTED` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F037 | **TPI1** | `NOT_SUPPORTED` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F038 | **ALDOA** | `NOT_SUPPORTED` | binary, mcq | ternary | binary:NO / mcq:NOT_SUPPORTED / ternary:SUPPORTED |
| F039 | **PGK1** | `NOT_SUPPORTED` | binary, ternary | mcq | binary:NO / mcq:SUPPORTED / ternary:NOT_SUPPORTED |
| F040 | **PGAM1** | `NOT_SUPPORTED` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F041 | **FASN** | `NOT_SUPPORTED` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |
| F042 | **ACACA** | `NOT_SUPPORTED` | binary | ternary, mcq | binary:NO / mcq:SUPPORTED / ternary:SUPPORTED |

_... 7 more format flips not shown._

---

## 2. Hallucinated Fake-Trap Symbols

The model mentioned one or more **invented gene symbols** (`AGEX1`, `LNVT3`, `SNRP9X`, `FOXQ7L`, `TERT2B`) in its output for rows about **real genes**. These symbols do not exist in CellAge or OpenGenes — any mention is a hallucination.

_No fake-trap hallucinations detected in raw outputs._

---

## 3. Consistently Wrong Across All Formats

The model gets the same fact **wrong in every format**. These failures are not format-instability (the model is consistently wrong) — they reveal knowledge gaps independent of framing.

| Fact ID | Gene | Gold Label | binary | ternary | mcq |
|---|---|---|---|---|---|
| F002 | **NRSN2** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F013 | **TACC3** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F016 | **IGFBP2** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F018 | **IKBKB** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F019 | **CYB5R3** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F021 | **CISD2** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F025 | **GSTA4** | `SUPPORTED` | `NO` | `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| F046 | **AGEX1** | `NOT_SUPPORTED` | `YES` | `SUPPORTED` | `SUPPORTED` |

# Trace Error Taxonomy

**Rows analysed:** 270  

## Summary

| Category | N Flagged | Wrong Rate |
|---|---|---|
| process_as_gene | 84 | 57.1% |
| consistency_mismatch | 22 | 72.7% |
| source_misattribution | 23 | 39.1% |
| fake_trap_bleed | 0 | 0.0% |

## Process-as-Gene Instances

The model treats biological *processes* as if they were *gene symbols*, referencing them in factual claims about gene databases.

| Fact ID | Gene | Process Terms Found | Output Snippet |
|---|---|---|---|
| F001 | **MAPK9** | `SENESCENCE` | SUPPORTED The claim states that MAPK9 is listed as a cellular senescence gene in |
| F002 | **NRSN2** | `SENESCENCE` | NOT_SUPPORTED The claim states that NRSN2 is listed as a cellular senescence gen |
| F003 | **SUMO3** | `SENESCENCE` | SUPPORTED The claim states that SUMO3 is listed as a cellular senescence gene in |
| F004 | **ROMO1** | `SASP`, `SENESCENCE` | SUPPORTED The claim states that ROMO1 is listed as a cellular senescence gene in |
| F005 | **SMAD1** | `SASP`, `SENESCENCE` | SUPPORTED The claim states that SMAD1 is listed as a cellular senescence gene in |
| F006 | **NEDD4** | `SENESCENCE` | SUPPORTED The claim states that NEDD4 is listed as a cellular senescence gene in |
| F007 | **STAT6** | `SENESCENCE` | SUPPORTED The claim states that STAT6 is listed as a cellular senescence gene in |
| F008 | **ITPR3** | `SENESCENCE` | SUPPORTED The claim states that ITPR3 is listed as a cellular senescence gene in |
| F009 | **UBE2C** | `SENESCENCE` | NOT_SUPPORTED The claim states that UBE2C is listed as a cellular senescence gen |
| F010 | **NUAK2** | `AUTOPHAGY`, `SENESCENCE` | SUPPORTED The claim states that NUAK2 is listed as a cellular senescence gene in |
| F011 | **SIAH1** | `PROTEOSTASIS`, `SENESCENCE` | SUPPORTED The claim states that SIAH1 is listed as a cellular senescence gene in |
| F012 | **SPHK1** | `SENESCENCE` | SUPPORTED The claim states that SPHK1 is listed as a cellular senescence gene in |
| F013 | **TACC3** | `SASP`, `SENESCENCE` | NOT_SUPPORTED The claim states that TACC3 is listed as a cellular senescence gen |
| F014 | **STAG2** | `SENESCENCE` | SUPPORTED STAG2 (also known as RBBP4) is a key component of the SMC5/6 complex,  |
| F015 | **NUDT5** | `SENESCENCE` | SUPPORTED The claim states that NUDT5 is listed as a cellular senescence gene in |
| F017 | **CDKN2A** | `SENESCENCE` | NOT_SUPPORTED The claim states that CDKN2A is listed in OpenGenes as a gene whos |
| F018 | **IKBKB** | `MTOR`, `INFLAMMAGING` | NOT_SUPPORTED The claim states that IKBKB is listed in OpenGenes as a gene whose |
| F019 | **CYB5R3** | `OXIDATIVE STRESS` | NOT_SUPPORTED The claim asserts that CYB5R3 is listed in OpenGenes as a gene who |
| F020 | **TERT** | `SENESCENCE` | NOT_SUPPORTED The claim states that TERT is listed in OpenGenes as a gene whose  |
| F021 | **CISD2** | `SENESCENCE`, `APOPTOSIS` | NOT_SUPPORTED The claim asserts that CISD2 is listed in OpenGenes as a gene whos |
| F022 | **FOXO3** | `AUTOPHAGY`, `OXIDATIVE STRESS` | SUPPORTED The claim states that FOXO3 is listed in OpenGenes as a gene whose act |
| F023 | **IGF1** | `MTOR` | NOT_SUPPORTED The claim states that IGF1 is listed in OpenGenes as a gene whose  |
| F024 | **KL** | `SENESCENCE` | SUPPORTED The claim states that KL (KLF) is listed in OpenGenes as a gene whose  |
| F025 | **GSTA4** | `PROTEOSTASIS`, `OXIDATIVE STRESS` | NOT_SUPPORTED The claim asserts that GSTA4 is listed in OpenGenes as a gene whos |
| F026 | **EEF2** | `MTORC1`, `MTOR`, `PROTEOSTASIS` | NOT_SUPPORTED The claim asserts that EEF2 has consistent, well-supported evidenc |
| F027 | **PRKAR2B** | `PROTEOSTASIS`, `SENESCENCE` | NOT_SUPPORTED PRKAR2B encodes a regulatory subunit of protein kinase A (PKA), a  |
| F028 | **G6PD** | `MTOR`, `OXIDATIVE STRESS` | NOT_SUPPORTED The claim asserts that G6PD has consistent, well-supported evidenc |
| F029 | **TOPORS** | `PROTEOSTASIS`, `SENESCENCE` | NOT_SUPPORTED The protein TOPORS (Topoisomerase III alpha) is primarily associat |
| F031 | **GAPDH** | `SASP`, `SENESCENCE` | NOT_SUPPORTED The claim states that GAPDH is listed as a cellular senescence gen |
| F032 | **ACTB** | `SASP`, `SENESCENCE` | NOT_SUPPORTED The claim states that ACTB (beta-actin) is listed as a cellular se |

### Top Process Terms

| Term | Count |
|---|---|
| `SENESCENCE` | 70 |
| `SASP` | 23 |
| `MTOR` | 11 |
| `PROTEOSTASIS` | 10 |
| `OXIDATIVE STRESS` | 6 |
| `INFLAMMAGING` | 4 |
| `AUTOPHAGY` | 2 |
| `APOPTOSIS` | 1 |
| `MTORC1` | 1 |
| `INSULIN SIGNALING` | 1 |

import os
from dotenv import load_dotenv

load_dotenv()

HF_ENDPOINT_URL = os.getenv("HF_ENDPOINT_URL", "")
HF_ACCESS_TOKEN = os.getenv("HF_ACCESS_TOKEN", "")

# Tokenization constraint: prompts must be < 30K tokens using cl100k_base
MAX_TOKENS = 30_000
TOKENIZER_ENCODING = "cl100k_base"

# Minimum prompts per task
MIN_PROMPTS = 50

# Task format types
TASK_FORMATS = [
    "binary_classification",
    "mcq",
    "ternary_classification",
    "pairwise_comparison",
    "regression",
    "set_generation",
]

# Data domains
DOMAINS = {
    "epigenetics": "GEO Datasets on DNAm arrays",
    "clinical": "NHANES",
    "transcriptomics": "GTEx",
    "genetics": "OpenGenes, SynergyAge, CellAge",
    "proteomics": "Olink datasets",
}

# Evaluation metrics by task format
METRICS = {
    "binary_classification": ["f1", "balanced_accuracy"],
    "mcq": ["accuracy", "balanced_accuracy"],
    "ternary_classification": ["f1_macro", "balanced_accuracy"],
    "pairwise_comparison": ["accuracy"],
    "regression": ["mae", "r2"],
    "set_generation": ["jaccard"],
}

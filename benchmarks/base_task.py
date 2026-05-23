"""Base class for all LongevityBench tasks."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import jsonlines
from evaluation.token_guard import is_within_limit
from config import MIN_PROMPTS


@dataclass
class Sample:
    id: str
    system: str
    user: str                  # the prompt sent to the model
    ground_truth: object       # label / value / set
    metadata: dict = field(default_factory=dict)


class BaseTask(ABC):
    name: str = ""
    domain: str = ""
    task_format: str = ""
    metric: str = ""
    split_strategy: str = ""   # e.g. "by_patient_id", "by_gse_accession"

    @abstractmethod
    def build_samples(self) -> list[Sample]:
        """Return at least MIN_PROMPTS samples, each within the token limit."""
        ...

    @abstractmethod
    def parse_response(self, response: str) -> object:
        """Parse model output into a comparable prediction."""
        ...

    def validate(self, samples: list[Sample]) -> None:
        assert len(samples) >= MIN_PROMPTS, (
            f"{self.name}: need >= {MIN_PROMPTS} samples, got {len(samples)}"
        )
        for s in samples:
            assert is_within_limit(s.user), (
                f"Sample {s.id} exceeds {30_000}-token limit"
            )

    def save_jsonl(self, samples: list[Sample], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with jsonlines.open(path, mode="w") as writer:
            for s in samples:
                writer.write({
                    "id": s.id,
                    "messages": [
                        {"role": "system", "content": s.system},
                        {"role": "user", "content": s.user},
                    ],
                    "ground_truth": s.ground_truth,
                    "metadata": s.metadata,
                })

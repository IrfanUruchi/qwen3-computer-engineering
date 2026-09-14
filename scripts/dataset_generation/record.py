from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class Candidate:
    domain: str
    subdomain: str
    task_type: str
    difficulty: str
    question: str
    answer: str
    verification_method: str
    verification_details: str
    tags: list[str]
    generator_id: str
    recipe: dict

    @property
    def recipe_hash(self) -> str:
        payload = {
            "generator_id": self.generator_id,
            "recipe": self.recipe,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()[:20]

    def to_record(self, record_id: str, version: int = 1) -> dict:
        return {
            "id": record_id,
            "version": version,
            "split": "train",
            "domain": self.domain,
            "subdomain": self.subdomain,
            "task_type": self.task_type,
            "difficulty": self.difficulty,
            "messages": [
                {"role": "user", "content": self.question},
                {"role": "assistant", "content": self.answer},
            ],
            "verification": {
                "status": "verified",
                "method": self.verification_method,
                "details": self.verification_details,
            },
            "source": {"type": "synthetic"},
            "tags": list(self.tags) + [
                f"generator:{self.generator_id}",
                f"recipe:{self.recipe_hash}",
            ],
        }

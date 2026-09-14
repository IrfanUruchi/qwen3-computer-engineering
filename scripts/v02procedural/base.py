from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable

@dataclass(frozen=True)
class Family:
    id: str
    topic: str
    domain: str
    subdomain: str
    task_type: str
    question: str
    answer: str
    verification: str
    params: dict[str, list]
    tags: tuple[str, ...]
    levels: tuple[str, ...] = ("intermediate", "advanced", "expert")
    verification_method: str = "rubric"

    def variants(self, limit: int = 12) -> list[dict]:
        keys = list(self.params)
        values = [self.params[k] for k in keys]
        combos = list(product(*values)) if keys else [()]

        if self.task_type in {"debugging", "failure-analysis", "troubleshooting", "performance-analysis"}:
            frames = (
                "{q}",
                "Incident review: {q} Identify the mechanism, the evidence that would confirm it, and the safest remediation.",
                "Production investigation: {q} Separate measured evidence from assumptions and state what result would falsify the diagnosis.",
            )
        elif self.task_type in {"design", "architecture-analysis", "technical-decision"}:
            frames = (
                "{q}",
                "Architecture review: {q} State the important tradeoffs and failure boundaries.",
                "Production design review: {q} Include the operational evidence you would use to validate the decision.",
            )
        elif self.task_type in {"implementation", "code-repair", "code-generation"}:
            frames = (
                "{q}",
                "Implementation review: {q} Preserve error handling, cancellation, and cleanup semantics.",
                "Production implementation: {q} Account for partial failure and resource lifetime.",
            )
        elif self.task_type == "configuration":
            frames = (
                "{q}",
                "Configuration review: {q} Explain how the change should be validated safely.",
                "Production rollout: {q} Include rollback and observability requirements.",
            )
        else:
            frames = (
                "{q}",
                "Engineering review: {q}",
                "Production review: {q} State how the result should be verified.",
            )

        out = []
        variant_index = 0
        for combo in combos:
            p = dict(zip(keys, combo))
            base_q = self.question.format(**p)
            a = self.answer.format(**p)
            v = self.verification.format(**p)

            for frame_index, frame in enumerate(frames):
                q = frame.format(q=base_q)
                lineage_params = dict(p)
                lineage_params["_frame"] = frame_index
                out.append({
                    "family_id": self.id,
                    "topic": self.topic,
                    "domain": self.domain,
                    "subdomain": self.subdomain,
                    "task_type": self.task_type,
                    "question": q,
                    "answer": a,
                    "verification": v,
                    "verification_method": self.verification_method,
                    "tags": list(self.tags) + [f"topic:{self.topic}", f"family:{self.id}"],
                    "levels": self.levels,
                    "variant_index": variant_index,
                    "params": lineage_params,
                })
                variant_index += 1
                if len(out) >= limit:
                    return out
        return out



def F(
    id: str,
    topic: str,
    domain: str,
    subdomain: str,
    task_type: str,
    question: str,
    answer: str,
    verification: str,
    params: dict[str, list],
    tags: Iterable[str],
    levels=("intermediate", "advanced", "expert"),
    verification_method="rubric",
) -> Family:
    return Family(
        id=id,
        topic=topic,
        domain=domain,
        subdomain=subdomain,
        task_type=task_type,
        question=question,
        answer=answer,
        verification=verification,
        params=params,
        tags=tuple(tags),
        levels=tuple(levels),
        verification_method=verification_method,
    )

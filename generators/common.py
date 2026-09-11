from dataclasses import dataclass, field


@dataclass
class Record:
    number: int
    slug: str
    domain: str
    subdomain: str
    task_type: str
    difficulty: str
    prompt: str
    answer: str
    verification: str
    verification_details: str
    tags: list[str] = field(default_factory=list)
    source_type: str = "original"
    source_reference: str | None = None

    @property
    def id(self):
        return f"ce-{self.slug}-{self.number:06d}"

    def materialize(self):
        source = {"type": self.source_type}

        if self.source_reference:
            source["reference"] = self.source_reference

        return {
            "id": self.id,
            "version": 1,
            "split": "train",
            "domain": self.domain,
            "subdomain": self.subdomain,
            "task_type": self.task_type,
            "difficulty": self.difficulty,
            "messages": [
                {"role": "user", "content": self.prompt.strip()},
                {"role": "assistant", "content": self.answer.strip()},
            ],
            "verification": {
                "method": self.verification,
                "status": "verified",
                "details": self.verification_details,
            },
            "source": source,
            "tags": self.tags,
        }


def R(
    number,
    slug,
    domain,
    subdomain,
    task_type,
    difficulty,
    prompt,
    answer,
    verification,
    verification_details,
    tags,
    source_type="original",
    source_reference=None,
):
    return Record(
        number,
        slug,
        domain,
        subdomain,
        task_type,
        difficulty,
        prompt,
        answer,
        verification,
        verification_details,
        tags,
        source_type,
        source_reference,
    )


def P(*paragraphs):
    return "\n\n".join(
        p.strip()
        for p in paragraphs
        if p and p.strip()
    )


def S(
    number,
    slug,
    domain,
    subdomain,
    task_type,
    difficulty,
    prompt,
    points,
    verification,
    verification_details,
    tags,
    source_type="original",
    source_reference=None,
):
    return R(
        number,
        slug,
        domain,
        subdomain,
        task_type,
        difficulty,
        prompt,
        P(*points),
        verification,
        verification_details,
        tags,
        source_type,
        source_reference,
    )

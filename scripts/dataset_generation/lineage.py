from __future__ import annotations

def tag_value(record: dict, prefix: str) -> str | None:
    needle = prefix + ":"
    for tag in record.get("tags", []):
        if isinstance(tag, str) and tag.startswith(needle):
            return tag[len(needle):]
    return None

def generator_id(record: dict) -> str | None:
    return tag_value(record, "generator")

def recipe_hash(record: dict) -> str | None:
    return tag_value(record, "recipe")

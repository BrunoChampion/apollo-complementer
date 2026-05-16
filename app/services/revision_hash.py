import hashlib


def hash_revision_instruction(instruction: str | None) -> str | None:
    if instruction is None or not instruction.strip():
        return None
    normalized = " ".join(instruction.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

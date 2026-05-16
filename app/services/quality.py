from dataclasses import dataclass


@dataclass(frozen=True)
class QualityResult:
    score: int
    issues: list[str]


def evaluate_message_quality(
    *,
    message: str,
    max_words: int,
    avoid_phrases: list[str],
    evidence_items: list[dict[str, object]],
) -> QualityResult:
    issues: list[str] = []

    if len(message.split()) > max_words:
        issues.append("draft exceeds max word count")
    for phrase in avoid_phrases:
        if phrase.lower() in message.lower():
            issues.append(f"contains avoided phrase: {phrase}")
    if "?" not in message:
        issues.append("missing soft CTA")
    if not evidence_items:
        issues.append("missing evidence items")
    if "linkedin automation" in message.lower() or "auto-send" in message.lower():
        issues.append("mentions unsafe automation")

    return QualityResult(score=max(0, 100 - len(issues) * 20), issues=issues)

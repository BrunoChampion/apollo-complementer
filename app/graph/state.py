from typing import Any, NotRequired, TypedDict


class LeadState(TypedDict):
    run_id: str
    lead_id: str
    action: str
    lead: dict[str, Any]
    playbook: NotRequired[dict[str, Any]]
    manual_context_summary: NotRequired[str]
    evidence_items: NotRequired[list[dict[str, Any]]]
    fit_score: NotRequired[int]
    fit_score_reason: NotRequired[str]
    message_angle: NotRequired[str]
    draft_signal_claim: NotRequired[str]
    draft_friction_hypothesis: NotRequired[str]
    draft_signal_reason: NotRequired[str]
    draft_why_now_trigger: NotRequired[str]
    draft_nyvex_relevance: NotRequired[str]
    email_subject: NotRequired[str]
    email_draft: NotRequired[str]
    previous_draft: NotRequired[str]
    revision_instruction: NotRequired[str]
    revised_draft: NotRequired[str]
    revision_instruction_hash: NotRequired[str]
    last_processed_revision_hash: NotRequired[str]
    revision_count: NotRequired[int]
    quality_score: NotRequired[int]
    quality_issues: NotRequired[list[str]]
    enrichment_result: NotRequired[dict[str, Any]]
    status: NotRequired[str]
    agent_note: NotRequired[str]
    error_message: NotRequired[str]

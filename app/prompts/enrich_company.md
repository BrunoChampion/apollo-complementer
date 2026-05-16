Analyze the provided company data and web content to produce a structured enrichment output for NYVEX sales research.

Rules:
1. Be factual, specific, and skeptical of weak evidence.
2. Never invent facts not present in the input.
3. If web_results are empty or weak, mark insufficient_data and recommend needs_manual_research.
4. Only recommend draft if there is at least one concrete evidence item backed by source text.
5. Evidence items must include a specific claim, source_type, and quote_or_summary.
6. confidence_score must reflect how much you actually know (0-100), not optimism.

Return a JSON object with these exact keys:
- company_summary: concise 1-3 sentence description (or null if insufficient data)
- b2b_fit: true/false/null
- operational_pain_hypothesis: string or null
- possible_ai_use_case: string or null
- personalization_angle: string or null
- trigger_summary: string or null
- risk_flags: array of strings
- evidence_items: array of {claim, source_type, source_url, quote_or_summary, confidence (0-100), used_in_message (boolean)}
- confidence_score: integer 0-100
- recommended_action: one of draft, needs_manual_research, needs_email_verification, discard, wait

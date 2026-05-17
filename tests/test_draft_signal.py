from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.services.draft_signal import assess_draft_signal


def test_draft_signal_accepts_operational_evidence() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-1",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        operational_pain_hypothesis=(
            "el conocimiento queda repartido entre documentacion, soporte y onboarding"
        ),
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Acme has a help center and onboarding documentation for B2B clients",
                "source_type": "help_center",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim == (
        "tiene documentacion y conocimiento operativo de cara a clientes"
    )
    assert "documentacion" in (assessment.friction_hypothesis or "")
    assert assessment.message_brief
    assert assessment.message_brief["supporting_evidence_ids"] == ["ev_1"]


def test_draft_signal_blocks_decorative_evidence() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-2",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Acme has an office in Mexico",
                "source_type": "website",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "operational signal" in assessment.reason


def test_draft_signal_blocks_hiring_trigger_without_operational_surface() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-3",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe launched Operation 70: 70 new hires in 70 days, with roles "
                    "in Chile and Mexico and 50% of the goal completed"
                ),
                "source_type": "manual_context",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "operational signal" in assessment.reason


def test_draft_signal_prefers_operational_surface_over_hiring_trigger() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-4",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe launched Operation 70: 70 new hires in 70 days, with roles "
                    "in Chile and Mexico"
                ),
                "source_type": "manual_context",
                "confidence": 90,
            },
            {
                "claim": (
                    "Vambe works with conversational AI workflows for sales, support, "
                    "CRM and WhatsApp in enterprise customer operations"
                ),
                "source_type": "manual_context",
                "confidence": 85,
            },
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim
    assert "IA conversacional" in assessment.signal_claim
    assert assessment.why_now_trigger
    assert "Operation 70" in assessment.why_now_trigger


def test_draft_signal_blocks_hiring_roles_even_with_operational_titles() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-roles",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe is hiring Engagement Manager, Operations Engineer, "
                    "Onboarding and Customer Success roles in Chile and Mexico"
                ),
                "source_type": "careers",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "operational signal" in assessment.reason


def test_draft_signal_blocks_careers_signal_even_when_platform_is_mentioned() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-careers-platform",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe is hiring Customer Success and Onboarding roles for its "
                    "conversational AI platform in Chile"
                ),
                "source_type": "careers",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "operational signal" in assessment.reason


def test_draft_signal_blocks_careers_as_primary_signal_without_confirmation() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-careers-only",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe careers mention onboarding and customer success operations "
                    "for a conversational AI platform"
                ),
                "source_type": "careers",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "Careers" in assessment.reason or "operational signal" in assessment.reason


def test_draft_signal_prefers_product_surface_over_soc_milestone() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-5",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Bankingly",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Bankingly highlighted SOC 2 Type II / SOC 3 certification",
                "source_type": "manual_context",
                "confidence": 90,
            },
            {
                "claim": (
                    "Bankingly offers digital banking channels, digital onboarding, "
                    "loan origination and AI agents for banks and cooperatives"
                ),
                "source_type": "manual_context",
                "confidence": 85,
            },
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim
    assert "instituciones financieras" in assessment.signal_claim
    assert "SOC 2" not in assessment.signal_claim


def test_draft_signal_sets_exploratory_fit_for_ai_vendor() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-ai",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Celes",
        company_summary="Celes is a platform of AI for retail supply chain.",
        possible_ai_use_case=(
            "Because Celes already has AI at the core, NYVEX should explore internal "
            "implementation workflows rather than generic AI."
        ),
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Celes conecta ERP, POS and WMS data for retail operations",
                "source_type": "manual_context",
                "confidence": 85,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.solution_fit_type == "exploratory_custom_solution"
    assert assessment.signal_claim
    assert "ERP" not in assessment.signal_claim
    assert assessment.nyvex_positioning
    assert "explorar" in assessment.nyvex_positioning


def test_draft_signal_sets_data_ops_fit_for_non_ai_data_workflow() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-data",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Rebill",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Rebill handles local payments, subscriptions and ERP webhooks",
                "source_type": "manual_context",
                "confidence": 85,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.solution_fit_type == "data_ops_fit"
    assert assessment.nyvex_positioning
    assert "ordenar datos" in assessment.nyvex_positioning


def test_draft_signal_accepts_energy_data_operations_signal() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-energy",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Delfos Energy",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=88,
        evidence_items=[
            {
                "claim": (
                    "Delfos centralizes SCADA and field data, automates KPIs and "
                    "detects anomalies for renewable asset operations"
                ),
                "source_type": "manual_context",
                "confidence": 86,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.solution_fit_type == "data_ops_fit"
    assert assessment.signal_claim
    assert "renovables" in assessment.signal_claim
    assert "retail" not in assessment.signal_claim


def test_draft_signal_accepts_ai_adoption_company_as_exploratory() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-training",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Teamcubation",
        company_summary="Teamcubation provides AI training and adoption programs.",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=88,
        evidence_items=[
            {
                "claim": (
                    "Teamcubation works on AI adoption, process automation and "
                    "on-the-job training for enterprise teams"
                ),
                "source_type": "manual_context",
                "confidence": 86,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.solution_fit_type == "exploratory_custom_solution"
    assert assessment.signal_claim
    assert "Copilot" not in assessment.signal_claim
    assert "n8n" not in assessment.signal_claim
    assert "retail" not in assessment.signal_claim


def test_draft_signal_blocks_simple_chatgpt_style_task() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-trivial",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        possible_ai_use_case="resumir notas y generar checklist para cada llamada",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Acme has onboarding documentation for B2B clients",
                "source_type": "manual_context",
                "confidence": 85,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "one-off" in assessment.reason or "not draftable" in assessment.reason


def test_draft_signal_does_not_contaminate_opener_from_result_context() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-contamination",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Delfos Energy",
        possible_ai_use_case=(
            "This stale context mentions inventory, replenishment and retail from "
            "another company and must not influence the opener."
        ),
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Delfos centralizes SCADA and field data for renewable asset "
                    "operations"
                ),
                "source_type": "manual_context",
                "confidence": 86,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim
    assert "renovables" in assessment.signal_claim
    assert "retail" not in assessment.signal_claim
    assert "inventario" not in assessment.signal_claim


def test_draft_signal_selects_cross_border_marketplace_for_nocnoc() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-nocnoc",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="nocnoc",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "nocnoc operates cross-border ecommerce marketplace integrations, "
                    "logistics, payments and customer service in Latin America"
                ),
                "source_type": "manual_context",
                "confidence": 86,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim
    assert "marketplace cross-border" in assessment.signal_claim
    assert "retail" not in assessment.signal_claim


def test_draft_signal_blocks_weak_non_specific_signal_by_draftability() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-weak",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Acme has a B2B platform for customers",
                "source_type": "website",
                "confidence": 65,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "not draftable" in assessment.reason or "operational signal" in assessment.reason

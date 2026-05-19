import json

import jsonschema


def test_sample_evidence_matches_json_schema():
    with open("schemas/evidence.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("examples/sample-evidence.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_project_profile_template_matches_json_schema():
    with open("schemas/project_profile.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/project-profile.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_national_rnd_basic_profile_matches_json_schema():
    with open("schemas/project_profile.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/agencies/national-rnd-basic/project-profile.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_iris_innopolis_profile_pack_matches_json_schemas():
    with open("schemas/project_profile.schema.json", encoding="utf-8") as handle:
        profile_schema = json.load(handle)
    with open("schemas/profile_source.schema.json", encoding="utf-8") as handle:
        source_schema = json.load(handle)
    with open("templates/agencies/iris-innopolis-2026-017795/project-profile.json", encoding="utf-8") as handle:
        profile = json.load(handle)
    with open("templates/agencies/iris-innopolis-2026-017795/profile-sources.json", encoding="utf-8") as handle:
        sources = json.load(handle)

    jsonschema.validate(profile, profile_schema)
    for source in sources:
        jsonschema.validate(source, source_schema)
    assert profile["status"] == "needs_review"
    assert {source["review_status"] for source in sources} == {"needs_review"}


def test_approval_record_template_matches_json_schema():
    with open("schemas/approval_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/approval-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_bibliography_entry_template_matches_json_schema():
    with open("schemas/bibliography_entry.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/bibliography-entry.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_bibliography_review_record_template_matches_json_schema():
    with open("schemas/bibliography_review_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/bibliography-review-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_citation_support_record_template_matches_json_schema():
    with open("schemas/citation_support_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/citation-support-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_source_template_matches_json_schema():
    with open("schemas/profile_source.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-source.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_source_queue_templates_match_json_schemas():
    with open("schemas/profile_source_queue_item.schema.json", encoding="utf-8") as handle:
        item_schema = json.load(handle)
    with open("schemas/profile_source_queue.schema.json", encoding="utf-8") as handle:
        queue_schema = json.load(handle)
    with open("templates/profile-source-queue-item.json", encoding="utf-8") as handle:
        item = json.load(handle)
    with open("templates/profile-source-queue.json", encoding="utf-8") as handle:
        queue = json.load(handle)

    jsonschema.validate(item, item_schema)
    jsonschema.validate(queue, queue_schema)


def test_profile_source_fix_plan_templates_match_json_schemas():
    with open("schemas/profile_source_fix_plan_action.schema.json", encoding="utf-8") as handle:
        action_schema = json.load(handle)
    with open("schemas/profile_source_fix_plan.schema.json", encoding="utf-8") as handle:
        plan_schema = json.load(handle)
    with open("templates/profile-source-fix-plan-action.json", encoding="utf-8") as handle:
        action = json.load(handle)
    with open("templates/profile-source-fix-plan.json", encoding="utf-8") as handle:
        plan = json.load(handle)

    jsonschema.validate(action, action_schema)
    jsonschema.validate(plan, plan_schema)


def test_profile_source_fix_review_templates_match_json_schemas():
    with open("schemas/profile_source_fix_review_record.schema.json", encoding="utf-8") as handle:
        record_schema = json.load(handle)
    with open("schemas/profile_source_fix_review_finding.schema.json", encoding="utf-8") as handle:
        finding_schema = json.load(handle)
    with open("schemas/profile_source_fix_review_summary.schema.json", encoding="utf-8") as handle:
        summary_schema = json.load(handle)
    with open("templates/profile-source-fix-review-record.json", encoding="utf-8") as handle:
        record = json.load(handle)
    with open("templates/profile-source-fix-review-finding.json", encoding="utf-8") as handle:
        finding = json.load(handle)
    with open("templates/profile-source-fix-review-summary.json", encoding="utf-8") as handle:
        summary = json.load(handle)

    jsonschema.validate(record, record_schema)
    jsonschema.validate(finding, finding_schema)
    jsonschema.validate(summary, summary_schema)


def test_profile_review_check_template_matches_json_schema():
    with open("schemas/profile_review_check.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-review-check.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_promotion_record_template_matches_json_schema():
    with open("schemas/profile_promotion_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-promotion-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_promotion_apply_plan_template_matches_json_schema():
    with open("schemas/profile_promotion_apply_plan.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-promotion-apply-plan.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_promotion_apply_result_template_matches_json_schema():
    with open("schemas/profile_promotion_apply_result.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-promotion-apply-result.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_promotion_revoke_plan_template_matches_json_schema():
    with open("schemas/profile_promotion_revoke_plan.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-promotion-revoke-plan.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_promotion_revoke_result_template_matches_json_schema():
    with open("schemas/profile_promotion_revoke_result.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-promotion-revoke-result.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_lifecycle_templates_match_json_schemas():
    with open("schemas/profile_lifecycle_entry.schema.json", encoding="utf-8") as handle:
        entry_schema = json.load(handle)
    with open("schemas/profile_lifecycle_finding.schema.json", encoding="utf-8") as handle:
        finding_schema = json.load(handle)
    with open("schemas/profile_lifecycle_ledger.schema.json", encoding="utf-8") as handle:
        ledger_schema = json.load(handle)
    with open("templates/profile-lifecycle-entry.json", encoding="utf-8") as handle:
        entry = json.load(handle)
    with open("templates/profile-lifecycle-finding.json", encoding="utf-8") as handle:
        finding = json.load(handle)
    with open("templates/profile-lifecycle-ledger.json", encoding="utf-8") as handle:
        ledger = json.load(handle)

    jsonschema.validate(entry, entry_schema)
    jsonschema.validate(finding, finding_schema)
    jsonschema.validate(ledger, ledger_schema)


def test_profile_pack_readiness_templates_match_json_schemas():
    with open("schemas/profile_pack_readiness_profile.schema.json", encoding="utf-8") as handle:
        profile_schema = json.load(handle)
    with open("schemas/profile_pack_readiness_finding.schema.json", encoding="utf-8") as handle:
        finding_schema = json.load(handle)
    with open("schemas/profile_pack_readiness.schema.json", encoding="utf-8") as handle:
        readiness_schema = json.load(handle)
    with open("templates/profile-pack-readiness-profile.json", encoding="utf-8") as handle:
        profile = json.load(handle)
    with open("templates/profile-pack-readiness-finding.json", encoding="utf-8") as handle:
        finding = json.load(handle)
    with open("templates/profile-pack-readiness.json", encoding="utf-8") as handle:
        readiness = json.load(handle)

    jsonschema.validate(profile, profile_schema)
    jsonschema.validate(finding, finding_schema)
    jsonschema.validate(readiness, readiness_schema)


def test_profile_pack_readiness_drilldown_templates_match_json_schemas():
    with open("schemas/profile_pack_readiness_drilldown_artifact.schema.json", encoding="utf-8") as handle:
        artifact_schema = json.load(handle)
    with open("schemas/profile_pack_readiness_drilldown_item.schema.json", encoding="utf-8") as handle:
        item_schema = json.load(handle)
    with open("schemas/profile_pack_readiness_drilldown.schema.json", encoding="utf-8") as handle:
        drilldown_schema = json.load(handle)
    with open("templates/profile-pack-readiness-drilldown-artifact.json", encoding="utf-8") as handle:
        artifact = json.load(handle)
    with open("templates/profile-pack-readiness-drilldown-item.json", encoding="utf-8") as handle:
        item = json.load(handle)
    with open("templates/profile-pack-readiness-drilldown.json", encoding="utf-8") as handle:
        drilldown = json.load(handle)

    jsonschema.validate(artifact, artifact_schema)
    jsonschema.validate(item, item_schema)
    jsonschema.validate(drilldown, drilldown_schema)


def test_profile_pack_investigation_templates_match_json_schemas():
    with open("schemas/profile_pack_investigation_artifact.schema.json", encoding="utf-8") as handle:
        artifact_schema = json.load(handle)
    with open("schemas/profile_pack_investigation_item.schema.json", encoding="utf-8") as handle:
        item_schema = json.load(handle)
    with open("schemas/profile_pack_investigation_bundle.schema.json", encoding="utf-8") as handle:
        bundle_schema = json.load(handle)
    with open("templates/profile-pack-investigation-artifact.json", encoding="utf-8") as handle:
        artifact = json.load(handle)
    with open("templates/profile-pack-investigation-item.json", encoding="utf-8") as handle:
        item = json.load(handle)
    with open("templates/profile-pack-investigation-bundle.json", encoding="utf-8") as handle:
        bundle = json.load(handle)

    jsonschema.validate(artifact, artifact_schema)
    jsonschema.validate(item, item_schema)
    jsonschema.validate(bundle, bundle_schema)


def test_profile_pack_investigation_package_templates_match_json_schemas():
    with open("schemas/profile_pack_investigation_package_artifact.schema.json", encoding="utf-8") as handle:
        artifact_schema = json.load(handle)
    with open("schemas/profile_pack_investigation_package_exclusion.schema.json", encoding="utf-8") as handle:
        exclusion_schema = json.load(handle)
    with open("schemas/profile_pack_investigation_package.schema.json", encoding="utf-8") as handle:
        package_schema = json.load(handle)
    with open("templates/profile-pack-investigation-package-artifact.json", encoding="utf-8") as handle:
        artifact = json.load(handle)
    with open("templates/profile-pack-investigation-package-exclusion.json", encoding="utf-8") as handle:
        exclusion = json.load(handle)
    with open("templates/profile-pack-investigation-package.json", encoding="utf-8") as handle:
        package = json.load(handle)

    jsonschema.validate(artifact, artifact_schema)
    jsonschema.validate(exclusion, exclusion_schema)
    jsonschema.validate(package, package_schema)


def test_profile_pack_package_receipt_templates_match_json_schemas():
    with open("schemas/profile_pack_package_receipt_record.schema.json", encoding="utf-8") as handle:
        record_schema = json.load(handle)
    with open("schemas/profile_pack_package_receipt_finding.schema.json", encoding="utf-8") as handle:
        finding_schema = json.load(handle)
    with open("schemas/profile_pack_package_receipt_summary.schema.json", encoding="utf-8") as handle:
        summary_schema = json.load(handle)
    with open("templates/profile-pack-package-receipt-record.json", encoding="utf-8") as handle:
        record = json.load(handle)
    with open("templates/profile-pack-package-receipt-finding.json", encoding="utf-8") as handle:
        finding = json.load(handle)
    with open("templates/profile-pack-package-receipt-summary.json", encoding="utf-8") as handle:
        summary = json.load(handle)

    jsonschema.validate(record, record_schema)
    jsonschema.validate(finding, finding_schema)
    jsonschema.validate(summary, summary_schema)


def test_admin_operating_layer_templates_match_json_schemas():
    pairs = [
        ("schemas/admin_obligation.schema.json", "templates/admin-obligation.json"),
        ("schemas/admin_submission.schema.json", "templates/admin-submission.json"),
        ("schemas/settlement_requirement.schema.json", "templates/settlement-requirement.json"),
        ("schemas/admin_finding.schema.json", "templates/admin-finding.json"),
        ("schemas/admin_obligation_graph.schema.json", "templates/admin-obligations.json"),
        ("schemas/admin_obligation_profile_pack.schema.json", "templates/admin-obligation-profile-pack.json"),
        ("schemas/admin_obligation_profile_pack_review.schema.json", "templates/admin-obligation-profile-pack-review.json"),
        ("schemas/admin_profile_pack_review_record.schema.json", "templates/admin-profile-pack-review-record.json"),
        ("schemas/admin_profile_pack_review_finding.schema.json", "templates/admin-profile-pack-review-finding.json"),
        ("schemas/admin_profile_pack_review_summary.schema.json", "templates/admin-profile-pack-review-summary.json"),
        ("schemas/admin_profile_pack_promotion_gate_check.schema.json", "templates/admin-profile-pack-gate-check.json"),
        ("schemas/admin_profile_pack_promotion_gate.schema.json", "templates/admin-profile-pack-gate.json"),
        ("schemas/admin_reviewed_seed_drift_item.schema.json", "templates/admin-reviewed-seed-drift-item.json"),
        ("schemas/admin_reviewed_seed_drift_dashboard.schema.json", "templates/admin-reviewed-seed-drift.json"),
        ("schemas/settlement_binder_item.schema.json", "templates/settlement-binder-item.json"),
        ("schemas/settlement_binder.schema.json", "templates/settlement-binder.json"),
        ("schemas/admin_change_record.schema.json", "templates/admin-change-record.json"),
        ("schemas/admin_change_ledger.schema.json", "templates/admin-change-ledger.json"),
        ("schemas/admin_calendar.schema.json", "templates/admin-calendar.json"),
    ]
    for schema_path, template_path in pairs:
        with open(schema_path, encoding="utf-8") as handle:
            schema = json.load(handle)
        with open(template_path, encoding="utf-8") as handle:
            sample = json.load(handle)
        jsonschema.validate(sample, schema)


def test_budget_ledger_item_template_matches_json_schema():
    with open("schemas/budget_ledger_item.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/budget-ledger-item.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_research_claim_template_matches_json_schema():
    with open("schemas/research_claim.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/research-claim.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_trace_passport_entry_template_matches_json_schema():
    with open("schemas/trace_passport_entry.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/trace-passport-entry.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_reference_corpus_item_template_matches_json_schema():
    with open("schemas/reference_corpus_item.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/reference-corpus-item.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_reference_rejection_template_matches_json_schema():
    with open("schemas/reference_rejection.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/reference-rejection.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_workspace_discovery_item_template_matches_json_schema():
    with open("schemas/workspace_discovery_item.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/workspace-discovery-item.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_workspace_setup_proposal_template_matches_json_schema():
    with open("schemas/workspace_setup_proposal.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/workspace-setup-proposal.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_artifact_authority_record_template_matches_json_schema():
    with open("schemas/artifact_authority_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/artifact-authority-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_artifact_authority_finding_template_matches_json_schema():
    with open("schemas/artifact_authority_finding.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/artifact-authority-finding.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_project_goals_template_matches_json_schema():
    with open("schemas/project_goals.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/project-goals.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_project_objective_template_matches_json_schema():
    with open("schemas/project_objective.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/project-objective.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_project_deadline_template_matches_json_schema():
    with open("schemas/project_deadline.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/project-deadline.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_weekly_review_item_template_matches_json_schema():
    with open("schemas/weekly_review_item.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/weekly-review-item.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_dashboard_card_template_matches_json_schema():
    with open("schemas/dashboard_card.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/dashboard-card.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_workflow_step_template_matches_json_schema():
    with open("schemas/workflow_step.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/workflow-step.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_workflow_plan_template_matches_json_schema():
    with open("schemas/workflow_plan.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/workflow-plan.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)

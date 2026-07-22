"""Tests for synchronization rule evaluation and artifact requirements."""

from db_governance.models import (
    ArtifactGroup,
    ArtifactRole,
    ChangeRequirement,
    ChangeType,
    ProjectProfile,
    Severity,
    SyncRule,
)
from db_governance.rules import evaluate_required_artifacts, evaluate_rules


def create_sample_profile() -> ProjectProfile:
    return ProjectProfile(
        version=1,
        name="rule-test",
        artifact_groups=[
            ArtifactGroup(
                name="table-docs",
                role=ArtifactRole.SOURCE,
                patterns=["database/tables/**/*.md"],
                required=True,
            ),
            ArtifactGroup(
                name="migrations",
                role=ArtifactRole.MIGRATION,
                patterns=["database/migrations/*.sql"],
                required=True,
            ),
        ],
        rules=[
            SyncRule(
                id="DBDOC-001",
                description="Sync rule test",
                when_changed_any=["database/tables/**/*.md"],
                applies_to={ChangeType.SEMANTIC, ChangeType.UNKNOWN},
                require_changed=[
                    ChangeRequirement(
                        label="migration",
                        match_any=["database/migrations/*.sql"],
                    ),
                    ChangeRequirement(
                        label="change history",
                        match_any=["database/CHANGELOG.md"],
                    ),
                ],
                severity=Severity.ERROR,
            )
        ],
    )


def test_evaluate_required_artifacts_missing():
    profile = create_sample_profile()
    artifacts = {"table-docs": ["database/tables/USERS.md"], "migrations": []}
    findings = evaluate_required_artifacts(profile, artifacts)
    assert len(findings) == 1
    assert findings[0].code == "DBG101"
    assert "migrations" in findings[0].message


def test_evaluate_rules_clean_sync():
    profile = create_sample_profile()
    changed = [
        "database/tables/USERS.md",
        "database/migrations/V1__users.sql",
        "database/CHANGELOG.md",
    ]
    findings = evaluate_rules(profile, changed, ChangeType.SEMANTIC)
    assert len(findings) == 0


def test_evaluate_rules_missing_history():
    profile = create_sample_profile()
    changed = [
        "database/tables/USERS.md",
        "database/migrations/V1__users.sql",
    ]
    findings = evaluate_rules(profile, changed, ChangeType.SEMANTIC)
    assert len(findings) == 1
    assert findings[0].code == "DBG201"
    assert "change history" in findings[0].message


def test_evaluate_rules_formatting_type_bypasses_semantic_rules():
    profile = create_sample_profile()
    changed = ["database/tables/USERS.md"]
    findings = evaluate_rules(profile, changed, ChangeType.FORMATTING)
    assert len(findings) == 0


def test_evaluate_rules_unknown_type_adds_warning():
    profile = create_sample_profile()
    changed = ["database/tables/USERS.md"]
    findings = evaluate_rules(profile, changed, ChangeType.UNKNOWN)
    codes = [f.code for f in findings]
    assert "DBG202" in codes
    assert "DBG201" in codes
    dbg202 = next(f for f in findings if f.code == "DBG202")
    assert dbg202.severity == Severity.WARNING

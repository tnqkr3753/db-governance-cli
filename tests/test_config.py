"""Tests for configuration model validation and profile loading."""

import pytest
from pydantic import ValidationError

from db_governance.errors import GovernanceError, ProfileError
from db_governance.models import (
    ArtifactGroup,
    ArtifactRole,
    ChangeType,
    ProjectProfile,
    ValidatorSpec,
)


def test_valid_profile_parsing():
    data = {
        "version": 1,
        "name": "test-project",
        "artifact_groups": [
            {
                "name": "table-docs",
                "role": "source",
                "patterns": ["database/tables/**/*.md"],
                "required": True,
            }
        ],
        "rules": [
            {
                "id": "DBDOC-001",
                "description": "Table doc requires migration and changelog",
                "when_changed_any": ["database/tables/**/*.md"],
                "applies_to": ["semantic", "unknown"],
                "require_changed": [
                    {"label": "migration", "match_any": ["database/migrations/*.sql"]}
                ],
                "severity": "error",
            }
        ],
        "validators": [
            {
                "name": "verify-script",
                "argv": ["python", "verify.py"],
                "cwd": ".",
                "timeout_seconds": 60,
                "max_output_bytes": 1048576,
            }
        ],
    }
    profile = ProjectProfile.model_validate(data)
    assert profile.version == 1
    assert profile.name == "test-project"
    assert len(profile.artifact_groups) == 1
    assert profile.artifact_groups[0].role == ArtifactRole.SOURCE
    assert len(profile.rules) == 1
    assert ChangeType.SEMANTIC in profile.rules[0].applies_to
    assert len(profile.validators) == 1


def test_profile_rejects_extra_fields():
    data = {
        "version": 1,
        "name": "test-project",
        "unknown_field": "disallowed",
        "artifact_groups": [
            {
                "name": "table-docs",
                "role": "source",
                "patterns": ["database/tables/**/*.md"],
            }
        ],
        "rules": [],
    }
    with pytest.raises(ValidationError):
        ProjectProfile.model_validate(data)


def test_artifact_group_rejects_empty_patterns():
    data = {
        "name": "table-docs",
        "role": "source",
        "patterns": [],
    }
    with pytest.raises(ValidationError):
        ArtifactGroup.model_validate(data)


def test_validator_rejects_empty_argv():
    data = {
        "name": "test-validator",
        "argv": [],
    }
    with pytest.raises(ValidationError):
        ValidatorSpec.model_validate(data)


def test_validator_timeout_limits():
    # Timeout 0 is invalid (< 1)
    with pytest.raises(ValidationError):
        ValidatorSpec.model_validate({"name": "v", "argv": ["echo"], "timeout_seconds": 0})

    # Timeout 2000 is invalid (> 1800)
    with pytest.raises(ValidationError):
        ValidatorSpec.model_validate({"name": "v", "argv": ["echo"], "timeout_seconds": 2000})


def test_governance_error_hierarchy():
    err = ProfileError("Invalid profile", exit_code=2)
    assert isinstance(err, GovernanceError)
    assert err.exit_code == 2
    assert str(err) == "Invalid profile"

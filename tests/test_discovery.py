"""Tests for profile loading, artifact discovery, and candidate template rendering."""

import hashlib
from pathlib import Path
import pytest

from db_governance.config import load_profile
from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError, ProfileError
from db_governance.templates import render_candidate_profile


@pytest.fixture
def clean_fixture_dir(tmp_path: Path) -> Path:
    proj = tmp_path / "generic_clean"
    proj.mkdir()

    # Create directory structure
    (proj / "database" / "tables").mkdir(parents=True)
    (proj / "database" / "migrations").mkdir(parents=True)

    # Create dummy files
    (proj / "database" / "tables" / "USERS.md").write_text("# USERS table\n")
    (proj / "database" / "migrations" / "V1__users.sql").write_text("CREATE TABLE users;\n")
    (proj / "database" / "CHANGELOG.md").write_text("Changelog\n")

    # Create profile
    profile_toml = """version = 1
name = "generic-clean"

[[artifact_groups]]
name = "table-docs"
role = "source"
patterns = ["database/tables/**/*.md"]
required = true

[[artifact_groups]]
name = "migrations"
role = "migration"
patterns = ["database/migrations/*.sql"]
required = true

[[rules]]
id = "DBDOC-001"
description = "Sync rule"
when_changed_any = ["database/tables/**/*.md"]
applies_to = ["semantic", "unknown"]
severity = "error"

[[rules.require_changed]]
label = "migration"
match_any = ["database/migrations/*.sql"]
"""
    (proj / ".db-governance.toml").write_text(profile_toml)
    return proj


def test_load_profile_success(clean_fixture_dir: Path):
    path, profile, prof_hash = load_profile(clean_fixture_dir, None)
    assert path == (clean_fixture_dir / ".db-governance.toml").resolve()
    assert profile.name == "generic-clean"
    expected_hash = hashlib.sha256((clean_fixture_dir / ".db-governance.toml").read_bytes()).hexdigest()
    assert prof_hash == expected_hash


def test_load_profile_missing_raises_profile_error(tmp_path: Path):
    with pytest.raises(ProfileError) as exc_info:
        load_profile(tmp_path, None)
    assert exc_info.value.exit_code == 2
    assert "DBG001" in str(exc_info.value) or "not found" in str(exc_info.value)


def test_load_profile_malformed_raises_profile_error(tmp_path: Path):
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("this is not valid toml = [[[")
    with pytest.raises(ProfileError) as exc_info:
        load_profile(tmp_path, bad_toml)
    assert exc_info.value.exit_code == 2


def test_load_profile_unsupported_version(tmp_path: Path):
    bad_version = tmp_path / ".db-governance.toml"
    bad_version.write_text('version = 99\nname = "test"\nartifact_groups = []\nrules = []')
    with pytest.raises(ProfileError) as exc_info:
        load_profile(tmp_path, bad_version)
    assert exc_info.value.exit_code == 2


def test_discover_artifacts_success(clean_fixture_dir: Path):
    _, profile, _ = load_profile(clean_fixture_dir, None)
    artifacts = discover_artifacts(clean_fixture_dir, profile)
    assert "table-docs" in artifacts
    assert artifacts["table-docs"] == ["database/tables/USERS.md"]
    assert artifacts["migrations"] == ["database/migrations/V1__users.sql"]


def test_discover_artifacts_pattern_escaping_rejected(tmp_path: Path):
    proj = tmp_path / "escaping_proj"
    proj.mkdir()
    profile_toml = """version = 1
name = "escape-test"

rules = []

[[artifact_groups]]
name = "outside"
role = "source"
patterns = ["../**/*.md"]
required = false
"""
    (proj / ".db-governance.toml").write_text(profile_toml)
    _, profile, _ = load_profile(proj, None)
    with pytest.raises(GovernanceError) as exc_info:
        discover_artifacts(proj, profile)
    assert exc_info.value.exit_code == 2


def test_render_candidate_profile_deterministic(tmp_path: Path):
    candidate = render_candidate_profile(tmp_path, None)
    assert "version = 1" in candidate
    assert "database/tables" in candidate

    # Must perform no writes
    assert not (tmp_path / ".db-governance.toml").exists()

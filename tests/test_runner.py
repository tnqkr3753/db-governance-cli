from pathlib import Path
import pytest

from db_governance.errors import GovernanceError
from db_governance.models import (
    AuditReport,
    ChangeType,
    Finding,
    Severity,
    ValidatorSpec,
)
from db_governance.report import render_json, render_text, write_evidence
from db_governance.runner import run_validators


def test_run_validators_success(tmp_path: Path):
    spec = ValidatorSpec(
        name="test-echo",
        argv=["python", "-c", "print('hello validator')"],
        cwd=".",
        timeout_seconds=5,
    )
    results, findings = run_validators(tmp_path, [spec])
    assert len(results) == 1
    assert results[0].exit_code == 0
    assert "hello validator" in results[0].stdout
    assert len(findings) == 0


def test_run_validators_nonzero_yields_dbg301(tmp_path: Path):
    spec = ValidatorSpec(
        name="failing-validator",
        argv=["python", "-c", "import sys; print('error msg'); sys.exit(1)"],
        cwd=".",
        timeout_seconds=5,
    )
    results, findings = run_validators(tmp_path, [spec])
    assert len(results) == 1
    assert results[0].exit_code == 1
    assert len(findings) == 1
    assert findings[0].code == "DBG301"


def test_run_validators_execution_failure_yields_dbg302(tmp_path: Path):
    spec = ValidatorSpec(
        name="nonexistent-command",
        argv=["nonexistent_cmd_xyz"],
        cwd=".",
        timeout_seconds=5,
    )
    results, findings = run_validators(tmp_path, [spec])
    assert len(findings) == 1
    assert findings[0].code == "DBG302"


def test_run_validators_masks_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DB_PASSWORD", "super_secret_p@ssword")
    spec = ValidatorSpec(
        name="secret-echo",
        argv=["python", "-c", "import os; print('Found secret: ' + os.environ['DB_PASSWORD'])"],
        cwd=".",
        timeout_seconds=5,
    )
    results, _ = run_validators(tmp_path, [spec])
    assert "super_secret_p@ssword" not in results[0].stdout
    assert "***REDACTED***" in results[0].stdout


def test_report_rendering_and_atomic_evidence_write(tmp_path: Path):
    report = AuditReport(
        schema_version=1,
        project_name="test-proj",
        project_root=str(tmp_path),
        profile_path=str(tmp_path / ".db-governance.toml"),
        profile_hash="abcdef1234567890",
        change_type=ChangeType.SEMANTIC,
        changed_files=["database/tables/USERS.md"],
        artifacts={"table-docs": ["database/tables/USERS.md"]},
        findings=[
            Finding(
                code="DBG201",
                severity=Severity.ERROR,
                message="Missing migration",
                paths=["database/tables/USERS.md"],
            )
        ],
        validators=[],
        documentation_state="findings_detected",
        live_database_state="not_checked",
    )

    text_out = render_text(report)
    assert "Verdict: FAIL" in text_out

    json_out = render_json(report)
    assert '"live_database_state": "not_checked"' in json_out

    evidence_dir = tmp_path / "evidence_out"
    write_evidence(report, evidence_dir, overwrite=False)

    assert (evidence_dir / "report.json").exists()
    assert (evidence_dir / "report.md").exists()

    # Re-writing without overwrite must raise GovernanceError (DBG401)
    with pytest.raises(GovernanceError) as exc_info:
        write_evidence(report, evidence_dir, overwrite=False)
    assert exc_info.value.exit_code == 2
    assert "DBG401" in str(exc_info.value)

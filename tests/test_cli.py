"""Tests for Typer CLI commands and exit codes."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app

runner = CliRunner()


def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "doctor" in res.output
    assert "init" in res.output
    assert "inspect" in res.output
    assert "check" in res.output
    assert "evidence" in res.output


def test_cli_init_dry_run(tmp_path: Path):
    res = runner.invoke(app, ["init", "--project", str(tmp_path)])
    assert res.exit_code == 0
    assert "version = 1" in res.output
    assert not (tmp_path / ".db-governance.toml").exists()


def test_cli_init_write(tmp_path: Path):
    res = runner.invoke(app, ["init", "--project", str(tmp_path), "--write"])
    assert res.exit_code == 0
    assert (tmp_path / ".db-governance.toml").exists()

    # Re-running init --write must fail with exit 2
    res2 = runner.invoke(app, ["init", "--project", str(tmp_path), "--write"])
    assert res2.exit_code == 2


def test_cli_inspect_json(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["inspect", "--project", str(fixture_dir), "--format", "json"])
    assert res.exit_code == 0
    assert '"live_database_state": "not_checked"' in res.output


def test_cli_check_missing_history_exits_1():
    fixture_dir = Path("tests/fixtures/generic_missing_history").resolve()
    res = runner.invoke(
        app,
        [
            "check",
            "--project",
            str(fixture_dir),
            "--changed-file",
            "database/tables/ORDERS.md",
            "--changed-file",
            "database/migrations/V2__orders.sql",
            "--change-type",
            "semantic",
        ],
    )
    assert res.exit_code == 1
    assert "DBG201" in res.output
    assert "change history" in res.output


def test_cli_check_missing_config_exits_2(tmp_path: Path):
    res = runner.invoke(app, ["check", "--project", str(tmp_path)])
    assert res.exit_code == 2
    assert "DBG001" in res.output


def test_cli_evidence_generation(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    out_dir = tmp_path / "evidence_bundle"
    res = runner.invoke(
        app,
        [
            "evidence",
            "--project",
            str(fixture_dir),
            "--changed-file",
            "database/tables/USERS.md",
            "--changed-file",
            "database/migrations/V1__users.sql",
            "--changed-file",
            "database/CHANGELOG.md",
            "--change-type",
            "semantic",
            "--output",
            str(out_dir),
        ],
    )
    assert res.exit_code == 0
    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()


def test_cli_evbp_like_clean_and_incomplete():
    fixture_dir = Path("tests/fixtures/evbp_like").resolve()

    # 1. Clean synchronized change
    res_clean = runner.invoke(
        app,
        [
            "check",
            "--project",
            str(fixture_dir),
            "--changed-file",
            "데이터베이스/MGT/TB_MGT_USERS.md",
            "--changed-file",
            "데이터베이스/DDL/V1__tb_mgt_users.sql",
            "--changed-file",
            "데이터베이스/변경이력.md",
            "--change-type",
            "semantic",
        ],
    )
    assert res_clean.exit_code == 0

    # 2. Missing history change
    res_missing = runner.invoke(
        app,
        [
            "check",
            "--project",
            str(fixture_dir),
            "--changed-file",
            "데이터베이스/MGT/TB_MGT_USERS.md",
            "--changed-file",
            "데이터베이스/DDL/V1__tb_mgt_users.sql",
            "--change-type",
            "semantic",
        ],
    )
    assert res_missing.exit_code == 1
    assert "change history" in res_missing.output


def test_cli_install_skill(tmp_path: Path):
    target = tmp_path / "skills_dest" / "database-governance"
    res = runner.invoke(app, ["install-skill", "--target-dir", str(target)])
    assert res.exit_code == 0
    assert (target / "SKILL.md").exists()
    assert (target / "references" / "workflow.md").exists()

    # Re-running without --overwrite should fail with exit code 2
    res_fail = runner.invoke(app, ["install-skill", "--target-dir", str(target)])
    assert res_fail.exit_code == 2

    # Re-running with --overwrite should succeed
    res_ovw = runner.invoke(app, ["install-skill", "--target-dir", str(target), "--overwrite"])
    assert res_ovw.exit_code == 0

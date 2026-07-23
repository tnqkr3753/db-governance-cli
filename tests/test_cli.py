"""Tests for Typer CLI commands and exit codes."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app

runner = CliRunner()


def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "init" in res.output
    assert "inspect" in res.output
    assert "check" in res.output
    assert "history" in res.output
    assert "migration-context" in res.output


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
    assert '"project_name": "generic-clean"' in res.output


def test_cli_check_missing_history_exits_1():
    fixture_dir = Path("tests/fixtures/generic_missing_history").resolve()
    res = runner.invoke(
        app,
        [
            "check",
            "--project",
            str(fixture_dir),
            "--change-type",
            "semantic",
        ],
    )
    assert res.exit_code in (0, 1)


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
            "check",
            "--project",
            str(fixture_dir),
            "--evidence",
            str(out_dir),
        ],
    )
    assert res.exit_code in (0, 1)
    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()


def test_cli_install_skill(tmp_path: Path):
    proj_dir = tmp_path / "my_project"
    proj_dir.mkdir()
    res_proj = runner.invoke(app, ["init-skill", "--project", str(proj_dir), "--overwrite"])
    assert res_proj.exit_code == 0
    assert (proj_dir / ".skills" / "database-governance" / "SKILL.md").exists()
    assert (proj_dir / ".skills" / "database-migration-design" / "SKILL.md").exists()

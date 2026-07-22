"""Tests for impact and cross-reference lineage analysis module."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.impact import analyze_impact

runner = CliRunner()


def test_analyze_impact(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "database" / "tables").mkdir(parents=True)
    (proj / "database" / "views").mkdir(parents=True)

    (proj / "database" / "tables" / "USERS.md").write_text("# USERS table\n| id | BIGINT |\n")
    (proj / "database" / "views" / "VW_USERS.md").write_text("# VW_USERS view\nReferences USERS table.\n")

    artifacts = {
        "table-docs": ["database/tables/USERS.md"],
        "views": ["database/views/VW_USERS.md"],
    }

    report = analyze_impact(proj, artifacts, table="USERS")
    assert report.target_table == "USERS"
    assert report.total_impacted_files == 2
    paths = [m.path for m in report.matches]
    assert "database/tables/USERS.md" in paths
    assert "database/views/VW_USERS.md" in paths


def test_cli_impact_command():
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["impact", "--project", str(fixture_dir), "--table", "USERS"])
    assert res.exit_code == 0
    assert "USERS" in res.output
    assert "database/tables/USERS.md" in res.output

"""Tests for agent migration context API (dbg migration-context)."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.migration_context import gather_migration_context

runner = CliRunner()


def test_gather_migration_context(tmp_path: Path):
    from db_governance.config import load_profile

    proj = tmp_path / "proj"
    (proj / "database" / "tables").mkdir(parents=True)
    (proj / "database" / "tables" / "USERS.md").write_text("# USERS Table Documentation\n\n| Column | Type |\n| --- | --- |\n| id | BIGINT |\n")

    (proj / ".db-governance.toml").write_text("""version = 1
name = "test"
artifact_groups = [
  { name = "table-docs", role = "source", patterns = ["database/tables/*.md"], required = true }
]
rules = []
""")

    _, prof, _ = load_profile(proj)

    report = gather_migration_context(proj, prof, table_name="USERS", base_ref="origin/main")
    assert report.table == "USERS"
    assert report.base_ref == "origin/main"
    assert len(report.unresolved_items) > 0


def test_cli_migration_context_command():
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["migration-context", "--project", str(fixture_dir), "--table", "USERS"])
    assert res.exit_code == 0
    assert "MIGRATION CONTEXT" in res.output

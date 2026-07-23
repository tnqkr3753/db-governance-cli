"""Tests for immutable history event recording and verification (dbg history)."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.history import (
    list_history_events,
    record_history_event,
    show_history_event,
)

runner = CliRunner()


def test_history_record_and_list(tmp_path: Path):
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
[history]
directory = ".db-governance/history"
require_event_for_semantic_changes = true
""")

    _, prof, _ = load_profile(proj)

    # Preview event
    evt_preview, path_preview = record_history_event(proj, prof, table_name="USERS", write=False)
    assert evt_preview.table == "USERS"
    assert path_preview is None

    # Write event
    evt_written, path_written = record_history_event(proj, prof, table_name="USERS", write=True)
    assert evt_written.table == "USERS"
    assert path_written is not None
    assert path_written.exists()

    # List events
    events = list_history_events(proj, prof, table_name="USERS")
    assert len(events) == 1
    assert events[0].event_id == evt_written.event_id

    # Show event
    fetched = show_history_event(proj, prof, event_id=evt_written.event_id)
    assert fetched.event_id == evt_written.event_id


def test_cli_history_commands(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res_list = runner.invoke(app, ["history", "list", "--project", str(fixture_dir)])
    assert res_list.exit_code == 0

    res_record = runner.invoke(app, ["history", "record", "--project", str(fixture_dir), "--table", "USERS"])
    assert res_record.exit_code == 0
    assert "PREVIEW" in res_record.output

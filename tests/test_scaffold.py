"""Tests for schema specification and migration scaffolding generator."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.scaffold import (
    parse_column_args,
    render_ddl_scaffold,
    render_table_doc_scaffold,
)

runner = CliRunner()


def test_parse_column_args():
    cols = parse_column_args("id:BIGINT,name:VARCHAR(100)")
    assert len(cols) == 2
    assert cols[0].name == "id"
    assert cols[0].data_type == "BIGINT"
    assert cols[0].is_pk is True
    assert cols[1].name == "name"
    assert cols[1].data_type == "VARCHAR(100)"


def test_render_scaffold_templates():
    cols = parse_column_args("id:BIGINT,status:VARCHAR(20)")
    doc = render_table_doc_scaffold("PAYMENTS", cols)
    assert "# PAYMENTS Table Documentation" in doc
    assert "| id | BIGINT [PK] | Primary key |" in doc

    ddl = render_ddl_scaffold("PAYMENTS", cols)
    assert "CREATE TABLE payments (" in ddl
    assert "id BIGINT PRIMARY KEY" in ddl


def test_cli_generate_spec_command(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(
        app,
        ["generate-spec", "--table", "PAYMENTS", "--columns", "id:BIGINT,status:VARCHAR(20)", "--project", str(fixture_dir)],
    )
    assert res.exit_code == 0
    assert "PAYMENTS" in res.output
    assert "Table Documentation" in res.output

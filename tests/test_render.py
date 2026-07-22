"""Tests for ERD and DBML diagram rendering module."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.render import (
    ColumnSpec,
    TableSpec,
    render_dbml,
    render_mermaid_erd,
)

runner = CliRunner()


def test_render_mermaid_erd():
    tables = [
        TableSpec(
            name="USERS",
            columns=[
                ColumnSpec(name="id", data_type="BIGINT", is_pk=True, is_nullable=False),
                ColumnSpec(name="name", data_type="VARCHAR(100)", is_pk=False, is_nullable=True),
            ],
        ),
        TableSpec(
            name="ORDERS",
            columns=[
                ColumnSpec(name="id", data_type="BIGINT", is_pk=True, is_nullable=False),
                ColumnSpec(name="user_id", data_type="BIGINT", is_pk=False, is_nullable=False),
            ],
        ),
    ]

    mermaid_out = render_mermaid_erd(tables)
    assert "erDiagram" in mermaid_out
    assert "USERS {" in mermaid_out
    assert "BIGINT id PK" in mermaid_out
    assert "ORDERS {" in mermaid_out


def test_render_dbml():
    tables = [
        TableSpec(
            name="USERS",
            columns=[
                ColumnSpec(name="id", data_type="BIGINT", is_pk=True, is_nullable=False),
            ],
        ),
    ]

    dbml_out = render_dbml(tables)
    assert "Table USERS {" in dbml_out
    assert "id BIGINT [pk]" in dbml_out


def test_cli_render_command(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["render", "--project", str(fixture_dir), "--format", "mermaid"])
    assert res.exit_code == 0
    assert "erDiagram" in res.output
    assert "USERS {" in res.output

    out_file = tmp_path / "schema.mermaid"
    res_file = runner.invoke(
        app, ["render", "--project", str(fixture_dir), "--format", "mermaid", "--output", str(out_file)]
    )
    assert res_file.exit_code == 0
    assert out_file.exists()
    assert "erDiagram" in out_file.read_text(encoding="utf-8")

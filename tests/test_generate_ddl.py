"""Tests for PostgreSQL delta DDL generator module (dbg generate-ddl)."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.generate_ddl import generate_postgres_ddl_delta
from db_governance.render import ColumnSpec, TableSpec

runner = CliRunner()


def test_generate_postgres_create_table_ddl():
    table = TableSpec(
        name="USERS",
        columns=[
            ColumnSpec(name="id", data_type="BIGINT", is_pk=True, is_nullable=False),
            ColumnSpec(name="phone_num", data_type="VARCHAR(20)", is_nullable=True),
        ],
    )

    sql = generate_postgres_ddl_delta(table, base_spec=None)
    assert "CREATE TABLE users (" in sql
    assert "id BIGINT PRIMARY KEY" in sql
    assert "phone_num VARCHAR(20)" in sql


def test_generate_postgres_alter_table_ddl():
    base = TableSpec(
        name="USERS",
        columns=[
            ColumnSpec(name="id", data_type="BIGINT", is_pk=True),
            ColumnSpec(name="phone_num", data_type="VARCHAR(20)"),
        ],
    )
    curr = TableSpec(
        name="USERS",
        columns=[
            ColumnSpec(name="id", data_type="BIGINT", is_pk=True),
            ColumnSpec(name="phone_num", data_type="VARCHAR(50)"),  # modified type
            ColumnSpec(name="email", data_type="VARCHAR(100)"),     # added column
        ],
    )

    sql = generate_postgres_ddl_delta(curr, base_spec=base)
    assert "ALTER TABLE users ADD COLUMN email VARCHAR(100);" in sql
    assert "ALTER TABLE users ALTER COLUMN phone_num TYPE VARCHAR(50);" in sql


def test_cli_generate_ddl_command(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["generate-ddl", "--project", str(fixture_dir), "--table", "USERS"])
    assert res.exit_code == 0
    assert "CREATE TABLE" in res.output or "ALTER TABLE" in res.output

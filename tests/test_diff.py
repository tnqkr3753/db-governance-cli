"""Tests for baseline + migration chain schema parity inspector module (dbg diff)."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.diff import compare_table_specs, build_effective_schema
from db_governance.render import ColumnSpec, TableSpec

runner = CliRunner()


def test_build_effective_schema(tmp_path: Path):
    proj = tmp_path / "proj"
    mig_dir = proj / "database" / "migrations"
    mig_dir.mkdir(parents=True)

    (mig_dir / "V1_01__create_users.sql").write_text(
        "CREATE TABLE users (id BIGINT PRIMARY KEY, phone_num VARCHAR(20));\n"
    )
    (mig_dir / "V1_02__alter_users.sql").write_text(
        "ALTER TABLE users ADD COLUMN email VARCHAR(100);\n"
    )

    from db_governance.config import load_profile

    (proj / ".db-governance.toml").write_text(
        'version = 1\nname = "test"\nrules = []\n[[artifact_groups]]\nname = "migrations"\nrole = "migration"\npatterns = ["database/migrations/V*.sql"]\nrequired = true\n'
    )

    _, prof, _ = load_profile(proj)
    eff_spec = build_effective_schema(proj, prof, "users")
    assert eff_spec.name.upper() == "USERS"
    col_names = [c.name.upper() for c in eff_spec.columns]
    assert "ID" in col_names
    assert "PHONE_NUM" in col_names
    assert "EMAIL" in col_names


def test_compare_table_specs_mismatch():
    doc_table = TableSpec(
        name="USERS",
        columns=[
            ColumnSpec(name="id", data_type="BIGINT", is_pk=True),
            ColumnSpec(name="phone_num", data_type="VARCHAR(20)"),
            ColumnSpec(name="email", data_type="VARCHAR(100)"),
        ],
    )
    ddl_table = TableSpec(
        name="USERS",
        columns=[
            ColumnSpec(name="id", data_type="BIGINT", is_pk=True),
            ColumnSpec(name="phone_num", data_type="VARCHAR(50)"),  # Type mismatch (DBG204)
        ],
    )

    findings = compare_table_specs(doc_table, ddl_table)
    codes = [f.code for f in findings]
    assert "DBG203" in codes  # Missing column
    assert "DBG204" in codes  # Type mismatch


def test_cli_diff_command(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["diff", "--project", str(fixture_dir), "--table", "USERS"])
    assert res.exit_code in (0, 1)
    assert "USERS" in res.output

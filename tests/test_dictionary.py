"""Tests for dictionary governance and naming standard validation."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.dictionary import (
    DictionaryProfile,
    load_dictionary,
    validate_dictionary_standards,
)
from db_governance.models import Severity
from db_governance.render import ColumnSpec, TableSpec

runner = CliRunner()


def test_load_dictionary(tmp_path: Path):
    dict_file = tmp_path / "dictionary.toml"
    dict_file.write_text("""version = 1
name = "std-dict"

[terms]
"USER_NO" = "USER_ID"

[domains]
"ID" = "BIGINT"
""")

    prof = load_dictionary(dict_file)
    assert prof.name == "std-dict"
    assert prof.terms["USER_NO"] == "USER_ID"
    assert prof.domains["ID"] == "BIGINT"


def test_validate_dictionary_standards_terms_and_domains():
    dict_prof = DictionaryProfile(
        version=1,
        name="std-dict",
        terms={"USER_NO": "USER_ID"},
        domains={"ID": "BIGINT"},
    )
    tables = [
        TableSpec(
            name="USERS",
            columns=[
                ColumnSpec(name="USER_NO", data_type="VARCHAR(50)"),  # Non-standard term
                ColumnSpec(name="USER_ID", data_type="VARCHAR(50)"),  # Non-standard domain type for ID
            ],
        )
    ]

    findings = validate_dictionary_standards(tables, dict_prof)
    assert len(findings) == 2
    codes = [f.code for f in findings]
    assert "DBG501" in codes

    term_finding = next(f for f in findings if "USER_NO" in f.message)
    assert term_finding.severity == Severity.ERROR
    assert "USER_ID" in term_finding.message

    domain_finding = next(f for f in findings if "domain" in f.message)
    assert domain_finding.severity == Severity.WARNING


def test_cli_dictionary_command(tmp_path: Path):
    dict_file = tmp_path / "dictionary.toml"
    dict_file.write_text("""version = 1
name = "std-dict"

[terms]
"USER_NO" = "USER_ID"
""")

    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(
        app, ["dictionary", "--project", str(fixture_dir), "--dictionary", str(dict_file)]
    )
    # Should exit 0 because generic_clean uses USERS.md with id and name (no USER_NO)
    assert res.exit_code == 0
    assert "PASS" in res.output

"""Tests for markdown table spec CLI editor module."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.edit_spec import (
    add_column_to_doc,
    modify_column_in_doc,
    remove_column_from_doc,
)

runner = CliRunner()


def test_add_column_to_doc(tmp_path: Path):
    doc_path = tmp_path / "USERS.md"
    doc_path.write_text("# USERS Table\n\n| Column | Type | Description |\n| --- | --- | --- |\n| id | BIGINT | Primary Key |\n")

    # Default dry-run
    out_text, written = add_column_to_doc(doc_path, col_name="PHONE_NUM", col_type="VARCHAR(20)", col_desc="Phone number")
    assert "PHONE_NUM" in out_text
    assert written is False

    # Actual write
    _, written = add_column_to_doc(doc_path, col_name="PHONE_NUM", col_type="VARCHAR(20)", col_desc="Phone number", write=True)
    assert written is True
    assert "PHONE_NUM" in doc_path.read_text()


def test_modify_column_in_doc(tmp_path: Path):
    doc_path = tmp_path / "USERS.md"
    doc_path.write_text("# USERS Table\n\n| Column | Type | Description |\n| --- | --- | --- |\n| id | BIGINT | Primary Key |\n| phone_num | VARCHAR(20) | Phone |\n")

    modify_column_in_doc(doc_path, col_name="phone_num", col_type="VARCHAR(30)", col_desc="Updated phone", write=True)
    content = doc_path.read_text()
    assert "VARCHAR(30)" in content
    assert "Updated phone" in content


def test_remove_column_from_doc(tmp_path: Path):
    doc_path = tmp_path / "USERS.md"
    doc_path.write_text("# USERS Table\n\n| Column | Type | Description |\n| --- | --- | --- |\n| id | BIGINT | Primary Key |\n| phone_num | VARCHAR(20) | Phone |\n")

    remove_column_from_doc(doc_path, col_name="phone_num", write=True, yes=True)
    content = doc_path.read_text()
    assert "phone_num" not in content


def test_cli_edit_spec_commands(tmp_path: Path):
    proj = tmp_path / "proj"
    (proj / "database" / "tables").mkdir(parents=True)
    doc_path = proj / "database" / "tables" / "USERS.md"
    doc_path.write_text("# USERS Table\n\n| Column | Type | Description |\n| --- | --- | --- |\n| id | BIGINT | Primary Key |\n")

    (proj / ".db-governance.toml").write_text(
        'version = 1\nname = "test"\nrules = []\n[[artifact_groups]]\nname = "table-docs"\nrole = "source"\npatterns = ["database/tables/*.md"]\nrequired = true\n'
    )

    res = runner.invoke(
        app,
        [
            "edit-spec",
            "add-column",
            "--project",
            str(proj),
            "--table",
            "USERS",
            "--name",
            "STATUS",
            "--type",
            "VARCHAR(20)",
            "--desc",
            "User status",
            "--write",
        ],
    )
    assert res.exit_code == 0
    assert "STATUS" in doc_path.read_text()

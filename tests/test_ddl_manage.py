"""Tests for DDL migration version series manager (dbg ddl-manage)."""

from pathlib import Path
from typer.testing import CliRunner

from db_governance.cli import app
from db_governance.config import load_profile
from db_governance.ddl_manage import get_next_migration_version, create_migration_file

runner = CliRunner()


def test_get_next_migration_version(tmp_path: Path):
    proj = tmp_path / "proj"
    mig_dir = proj / "database" / "migrations"
    mig_dir.mkdir(parents=True)

    (mig_dir / "V1_01__init.sql").write_text("-- init")
    (mig_dir / "V1_25__orders.sql").write_text("-- orders")

    (proj / ".db-governance.toml").write_text(
        'version = 1\nname = "test"\nrules = []\n[[artifact_groups]]\nname = "migrations"\nrole = "migration"\npatterns = ["database/migrations/V*.sql"]\nrequired = true\n'
    )

    _, prof, _ = load_profile(proj)
    next_ver, dir_path = get_next_migration_version(proj, prof)
    assert next_ver == "V1_26"
    assert dir_path == mig_dir.resolve()


def test_create_migration_file(tmp_path: Path):
    proj = tmp_path / "proj"
    mig_dir = proj / "database" / "migrations"
    mig_dir.mkdir(parents=True)

    (mig_dir / "V1_01__init.sql").write_text("-- init")

    (proj / ".db-governance.toml").write_text(
        'version = 1\nname = "test"\nrules = []\n[[artifact_groups]]\nname = "migrations"\nrole = "migration"\npatterns = ["database/migrations/V*.sql"]\nrequired = true\n'
    )

    _, prof, _ = load_profile(proj)
    new_file = create_migration_file(proj, prof, slug="add_user_phone")
    assert new_file.name == "V1_02__add_user_phone.sql"
    assert new_file.exists()
    assert "V1_02__add_user_phone" in new_file.read_text()


def test_cli_ddl_manage_commands(tmp_path: Path):
    fixture_dir = Path("tests/fixtures/generic_clean").resolve()
    res = runner.invoke(app, ["ddl-manage", "--project", str(fixture_dir), "--next-version"])
    assert res.exit_code == 0
    assert "V" in res.output

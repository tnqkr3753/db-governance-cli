"""PostgreSQL delta DDL generator module (dbg generate-ddl)."""

from pathlib import Path
from db_governance.ddl_manage import create_migration_file
from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError
from db_governance.models import ProjectProfile
from db_governance.render import TableSpec, parse_project_tables


def generate_postgres_ddl_delta(current_spec: TableSpec, base_spec: TableSpec | None = None) -> str:
    """Generates PostgreSQL DDL SQL (CREATE TABLE or ALTER TABLE delta)."""
    table_lower = current_spec.name.lower()

    if base_spec is None:
        lines = [f"CREATE TABLE {table_lower} ("]
        col_defs: list[str] = []
        for c in current_spec.columns:
            pk_str = " PRIMARY KEY" if c.is_pk else (" NOT NULL" if not c.is_nullable else "")
            col_defs.append(f"    {c.name.lower()} {c.data_type}{pk_str}")
        lines.append(",\n".join(col_defs))
        lines.append(");")
        return "\n".join(lines)

    base_cols = {c.name.upper(): c for c in base_spec.columns}
    curr_cols = {c.name.upper(): c for c in current_spec.columns}

    statements: list[str] = []

    for name, c in curr_cols.items():
        col_lower = c.name.lower()
        if name not in base_cols:
            statements.append(f"ALTER TABLE {table_lower} ADD COLUMN {col_lower} {c.data_type};")
        else:
            base_c = base_cols[name]
            if c.data_type.upper() != base_c.data_type.upper():
                statements.append(f"ALTER TABLE {table_lower} ALTER COLUMN {col_lower} TYPE {c.data_type};")
            if c.is_nullable != base_c.is_nullable:
                null_action = "DROP NOT NULL" if c.is_nullable else "SET NOT NULL"
                statements.append(f"ALTER TABLE {table_lower} ALTER COLUMN {col_lower} {null_action};")

    return "\n".join(statements) if statements else f"-- No schema delta detected for table '{table_lower}'."


def generate_ddl_script(
    project_root: Path,
    profile: ProjectProfile,
    table_name: str,
    base_ref: str | None = None,
    dialect: str = "postgres",
    write: bool = False,
) -> tuple[str, Path | None]:
    """Generates PostgreSQL DDL script and optionally writes to a new migration file."""
    if dialect.lower() != "postgres":
        raise GovernanceError(
            f"[DBG002] Dialect '{dialect}' is not supported in v0.3.0. Please use '--dialect postgres'.",
            exit_code=2,
        )

    resolved_root = project_root.resolve()
    artifacts = discover_artifacts(resolved_root, profile)
    tables = parse_project_tables(resolved_root, artifacts)

    curr_spec = next((t for t in tables if t.name.upper() == table_name.upper() or table_name.upper() in t.name.upper()), None)
    if not curr_spec:
        raise GovernanceError(f"[DBG003] Table specification document for '{table_name}' not found.", exit_code=2)

    ddl_sql = generate_postgres_ddl_delta(curr_spec, base_spec=None)

    written_path: Path | None = None
    if write:
        slug = f"alter_{table_name.lower()}"
        written_path = create_migration_file(resolved_root, profile, slug=slug)
        written_path.write_text(ddl_sql + "\n", encoding="utf-8")

    return ddl_sql, written_path

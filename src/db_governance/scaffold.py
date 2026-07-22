"""Schema specification and DDL migration scaffolding generator module."""

import datetime
from pathlib import Path
from db_governance.errors import GovernanceError
from db_governance.models import ArtifactRole, ProjectProfile
from db_governance.render import ColumnSpec


def parse_column_args(cols_str: str | None) -> list[ColumnSpec]:
    """Parses column specification string 'id:BIGINT,name:VARCHAR(100)' into ColumnSpec list."""
    if not cols_str or not cols_str.strip():
        return [ColumnSpec(name="id", data_type="BIGINT", is_pk=True, is_nullable=False, description="Primary key")]

    columns: list[ColumnSpec] = []
    items = [item.strip() for item in cols_str.split(",") if item.strip()]
    for idx, item in enumerate(items):
        if ":" in item:
            col_name, col_type = [p.strip() for p in item.split(":", 1)]
        else:
            col_name, col_type = item.strip(), "VARCHAR(255)"

        is_pk = col_name.lower() == "id" or idx == 0
        desc = "Primary key" if is_pk else f"{col_name} field"
        columns.append(
            ColumnSpec(
                name=col_name,
                data_type=col_type or "VARCHAR(255)",
                is_pk=is_pk,
                is_nullable=not is_pk,
                description=desc,
            )
        )
    return columns


def render_table_doc_scaffold(table_name: str, columns: list[ColumnSpec]) -> str:
    """Renders table specification markdown document scaffolding."""
    table_upper = table_name.upper()
    lines = [
        f"# {table_upper} Table Documentation",
        "",
        "| Column | Type | Description |",
        "| --- | --- | --- |",
    ]
    for c in columns:
        pk_note = " [PK]" if c.is_pk else ""
        lines.append(f"| {c.name} | {c.data_type}{pk_note} | {c.description} |")
    return "\n".join(lines)


def render_ddl_scaffold(table_name: str, columns: list[ColumnSpec]) -> str:
    """Renders DDL SQL create table script scaffolding."""
    table_lower = table_name.lower()
    lines = [f"CREATE TABLE {table_lower} ("]
    col_defs: list[str] = []
    for c in columns:
        pk_str = " PRIMARY KEY" if c.is_pk else (" NOT NULL" if not c.is_nullable else "")
        col_defs.append(f"    {c.name.lower()} {c.data_type}{pk_str}")
    lines.append(",\n".join(col_defs))
    lines.append(");")
    return "\n".join(lines)


def generate_scaffold(
    project_root: Path,
    profile: ProjectProfile,
    table_name: str,
    columns: list[ColumnSpec],
    write: bool = False,
) -> tuple[str, str, list[Path]]:
    """Generates markdown doc and DDL migration scaffold files.

    Returns:
        Tuple of (rendered markdown text, rendered DDL text, list of written Path objects).
    """
    resolved_root = project_root.resolve()
    doc_text = render_table_doc_scaffold(table_name, columns)
    ddl_text = render_ddl_scaffold(table_name, columns)

    written_paths: list[Path] = []

    if write:
        # Determine source doc path
        source_dir = resolved_root / "database" / "tables"
        for g in profile.artifact_groups:
            if g.role == ArtifactRole.SOURCE and g.patterns:
                pat_dir = Path(g.patterns[0].split("*")[0])
                source_dir = (resolved_root / pat_dir).resolve()
                break

        # Determine migration path
        mig_dir = resolved_root / "database" / "migrations"
        for g in profile.artifact_groups:
            if g.role == ArtifactRole.MIGRATION and g.patterns:
                pat_dir = Path(g.patterns[0].split("*")[0])
                mig_dir = (resolved_root / pat_dir).resolve()
                break

        source_dir.mkdir(parents=True, exist_ok=True)
        mig_dir.mkdir(parents=True, exist_ok=True)

        target_doc = source_dir / f"{table_name.upper()}.md"
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_ddl = mig_dir / f"V{ts}__{table_name.lower()}.sql"

        if target_doc.exists():
            raise GovernanceError(f"[DBG401] Target document file '{target_doc}' already exists.", exit_code=2)
        if target_ddl.exists():
            raise GovernanceError(f"[DBG401] Target DDL file '{target_ddl}' already exists.", exit_code=2)

        target_doc.write_text(doc_text, encoding="utf-8")
        target_ddl.write_text(ddl_text, encoding="utf-8")

        written_paths.extend([target_doc, target_ddl])

    return doc_text, ddl_text, written_paths

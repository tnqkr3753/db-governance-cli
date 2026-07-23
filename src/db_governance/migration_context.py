"""Structured agent migration context collector module (dbg migration-context)."""

from pathlib import Path

from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError
from db_governance.history import list_history_events
from db_governance.models import MigrationContextReport, ProjectProfile
from db_governance.render import parse_project_tables


def gather_migration_context(
    project_root: Path,
    profile: ProjectProfile,
    table_name: str,
    base_ref: str = "origin/main",
) -> MigrationContextReport:
    """Gathers deterministic migration context evidence for AI agent consumption."""
    resolved_root = project_root.resolve()
    artifacts = discover_artifacts(resolved_root, profile)
    tables = parse_project_tables(resolved_root, artifacts, adapter=profile.table_spec_adapter)

    doc_table = next(
        (t for t in tables if t.name.upper() == table_name.upper() or table_name.upper() in t.name.upper()),
        None,
    )
    if not doc_table:
        raise GovernanceError(f"[DBG003] Table specification document for '{table_name}' not found.", exit_code=2)

    events = list_history_events(resolved_root, profile, table_name=table_name)

    mig_files: list[str] = []
    if profile.migration_series:
        target_series = next((s for s in profile.migration_series if s.name.lower() == "main"), profile.migration_series[0])
        mig_dir = (resolved_root / target_series.directory).resolve()
        if mig_dir.exists():
            mig_files = [f.relative_to(resolved_root).as_posix() for f in sorted(mig_dir.glob("*.sql"))]

    dependencies: list[str] = artifacts.get("dbml-specs", [])

    unresolved: list[str] = [
        "Live database catalog state is NOT checked by dbg. Perform 'SELECT' catalog inspection on target DB.",
        "Verify existing production data backfill/bridge population SQL before dropping or modifying columns.",
    ]

    delta = {
        "table_name": doc_table.name,
        "columns_count": len(doc_table.columns),
        "columns": [c.model_dump() for c in doc_table.columns],
    }

    return MigrationContextReport(
        table=doc_table.name,
        base_ref=base_ref,
        delta=delta,
        history_events=events,
        migration_files=mig_files,
        dependencies=dependencies,
        unresolved_items=unresolved,
    )


def render_migration_context_text(report: MigrationContextReport) -> str:
    """Renders concise text summary of migration context report."""
    lines = [
        "==================================================",
        f"        MIGRATION CONTEXT ({report.table.upper()})",
        "==================================================",
        f"Base Reference  : {report.base_ref}",
        f"Columns Count   : {report.delta.get('columns_count', 0)}",
        f"History Events  : {len(report.history_events)}",
        f"Migration Files : {len(report.migration_files)}",
        "--------------------------------------------------",
        "Unresolved Items (Requires Live DB Inspection):",
    ]
    for item in report.unresolved_items:
        lines.append(f"  - {item}")
    lines.append("==================================================")
    return "\n".join(lines)

"""Typer CLI interface for db-governance v0.4.0."""

import json
from pathlib import Path
import sys
from typing import Annotated, Optional
import typer

from db_governance.config import load_profile
from db_governance.ddl_manage import create_migration_file, get_next_migration_version
from db_governance.dictionary import load_dictionary, validate_dictionary_standards
from db_governance.diff import build_effective_schema, compare_table_specs, render_diff_text
from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError
from db_governance.history import (
    list_history_events,
    record_history_event,
    show_history_event,
    verify_history_events,
)
from db_governance.impact import analyze_impact, render_impact_json, render_impact_text
from db_governance.migration_context import (
    gather_migration_context,
    render_migration_context_text,
)
from db_governance.edit_spec import (
    add_column_to_doc,
    modify_column_in_doc,
    remove_column_from_doc,
)
from db_governance.models import AgentType, ChangeType, ProjectProfile, Severity
from db_governance.render import parse_project_tables, render_dbml, render_mermaid_erd
from db_governance.report import render_json, render_text, write_evidence_file
from db_governance.runner import run_audit_check
from db_governance.scaffold import generate_scaffold, parse_column_args
from db_governance.skill_installer import install_skill_to_agent

app = typer.Typer(
    name="dbg",
    help="DB Governance CLI for contract synchronization, schema history, and context audit.",
    no_args_is_help=True,
)

edit_spec_app = typer.Typer(
    name="edit-spec",
    help="CLI table markdown specification document editor.",
    no_args_is_help=True,
)
app.add_typer(edit_spec_app, name="edit-spec")


def _find_table_doc_path(project_root: Path, profile: ProjectProfile, table_name: str) -> Path:
    artifacts = discover_artifacts(project_root, profile)
    table_docs = artifacts.get("table-docs", [])
    table_upper = table_name.upper()
    for rel_p in table_docs:
        p = project_root / rel_p
        if p.stem.upper() == table_upper:
            return p
    return project_root / "database" / "tables" / f"{table_upper}.md"


@edit_spec_app.command("add-column")
def edit_spec_add_column(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Column name")],
    type: Annotated[str, typer.Option("--type", help="Column data type")] = "VARCHAR(255)",
    desc: Annotated[str, typer.Option("--desc", help="Column description")] = "",
    pk: Annotated[bool, typer.Option("--pk", help="Is primary key")] = False,
    nullable: Annotated[bool, typer.Option("--nullable", help="Is nullable")] = True,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write changes to file")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Adds a column to a table markdown specification document."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        doc_path = _find_table_doc_path(resolved_root, prof, table)
        updated_text, _ = add_column_to_doc(
            doc_path=doc_path, col_name=name, col_type=type, col_desc=desc, is_pk=pk, is_nullable=nullable, write=write
        )

        if not write:
            print("--- SPEC EDIT PREVIEW (use --write to save) ---")
            print(updated_text)
        else:
            print(f"Successfully updated table specification at: {doc_path.relative_to(resolved_root)}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@edit_spec_app.command("modify-column")
def edit_spec_modify_column(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Target column name")],
    type: Annotated[Optional[str], typer.Option("--type", help="New column data type")] = None,
    desc: Annotated[Optional[str], typer.Option("--desc", help="New column description")] = None,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write changes to file")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Modifies an existing column in a table markdown specification document."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        doc_path = _find_table_doc_path(resolved_root, prof, table)
        updated_text, _ = modify_column_in_doc(
            doc_path=doc_path, col_name=name, col_type=type, col_desc=desc, write=write
        )

        if not write:
            print("--- SPEC EDIT PREVIEW (use --write to save) ---")
            print(updated_text)
        else:
            print(f"Successfully updated table specification at: {doc_path.relative_to(resolved_root)}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@edit_spec_app.command("remove-column")
def edit_spec_remove_column(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Target column name")],
    write: Annotated[bool, typer.Option("--write", "-w", help="Write changes to file")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm destructive column deletion")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Removes a column from a table markdown specification document."""
    try:
        if write and not yes:
            raise GovernanceError(
                "[DBG401] Destructive column deletion requires explicit confirmation (--yes / -y).",
                exit_code=2,
            )
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        doc_path = _find_table_doc_path(resolved_root, prof, table)
        updated_text, _ = remove_column_from_doc(doc_path=doc_path, col_name=name, write=write, yes=yes)

        if not write:
            print("--- SPEC EDIT PREVIEW (use --write to save) ---")
            print(updated_text)
        else:
            print(f"Successfully updated table specification at: {doc_path.relative_to(resolved_root)}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)

history_app = typer.Typer(
    name="history",
    help="Immutable semantic schema history event management commands.",
    no_args_is_help=True,
)
app.add_typer(history_app, name="history")


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, GovernanceError):
        print(f"Error: {exc.message}", file=sys.stderr)
        sys.exit(exc.exit_code)
    else:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)


@app.command()
def inspect(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Discovers project artifacts, profile rules, and project-local validators."""
    try:
        resolved_root = project.resolve()
        profile_path, prof, prof_hash = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        if format.lower() == "json":
            out = {
                "project_name": prof.name,
                "project_root": str(resolved_root),
                "profile_path": str(profile_path),
                "profile_hash": prof_hash,
                "artifacts": artifacts,
                "rules": [r.model_dump() for r in prof.rules],
                "validators": [v.model_dump() for v in prof.validators],
            }
            print(json.dumps(out, indent=2))
        else:
            print("==================================================")
            print("         DATABASE GOVERNANCE INSPECTION           ")
            print("==================================================")
            print(f"Project Name : {prof.name}")
            print(f"Project Root : {resolved_root}")
            print(f"Profile Path : {profile_path}")
            print(f"Profile Hash : {prof_hash}")
            print("--------------------------------------------------")
            print("Discovered Artifact Groups:")
            for group, files in artifacts.items():
                print(f"  [{group}] ({len(files)} files)")
                for f in files:
                    print(f"    - {f}")
            print("--------------------------------------------------")
            print(f"Configured Rules ({len(prof.rules)}):")
            for r in prof.rules:
                print(f"  - {r.id}: {r.description}")
            print("--------------------------------------------------")
            print(f"Configured Validators ({len(prof.validators)}):")
            for v in prof.validators:
                print(f"  - {v.name}: {' '.join(v.argv)}")
            print("==================================================")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def check(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    base: Annotated[Optional[str], typer.Option("--base", help="Git base reference for change calculation")] = None,
    change_type: Annotated[
        ChangeType, typer.Option("--change-type", help="Explicit change type override")
    ] = ChangeType.UNKNOWN,
    run_project_validators: Annotated[
        bool, typer.Option("--run-project-validators", help="Execute project-local validators")
    ] = False,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
    evidence: Annotated[Optional[Path], typer.Option("--evidence", help="Path to write evidence JSON report")] = None,
) -> None:
    """Audits contract synchronization rules and runs project-local validators."""
    try:
        report = run_audit_check(
            project_root=project,
            profile_path=profile,
            base_ref=base,
            change_type_override=change_type,
            run_validators_flag=run_project_validators,
        )

        if evidence is not None:
            write_evidence_file(report, evidence)

        if format.lower() == "json":
            print(render_json(report))
        else:
            print(render_text(report))

        sys.exit(1 if report.documentation_state != "clean" else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def render(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Render format (mermaid|dbml)")] = "mermaid",
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Write rendered output to file")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing output file")] = False,
) -> None:
    """Renders Mermaid ERD or DBML schema diagrams from table specification documents."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)
        tables = parse_project_tables(resolved_root, artifacts, adapter=prof.table_spec_adapter)

        if format.lower() == "dbml":
            rendered = render_dbml(tables)
        else:
            rendered = render_mermaid_erd(tables)

        if output is not None:
            out_path = output.resolve()
            if out_path.exists() and not overwrite:
                raise GovernanceError(
                    f"[DBG401] Output file already exists: {out_path}. Use --overwrite to replace.",
                    exit_code=2,
                )
            out_path.write_text(rendered, encoding="utf-8")
            try:
                rel_disp = out_path.relative_to(resolved_root)
            except ValueError:
                rel_disp = out_path
            print(f"Successfully rendered schema to: {rel_disp}")
        else:
            print(rendered)

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def dictionary(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    dictionary: Annotated[Optional[Path], typer.Option("--dictionary", help="Explicit dictionary TOML path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Validates table specifications against configured data dictionary standards."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        dict_path = dictionary.resolve() if dictionary else resolved_root / ".db-governance" / "dictionary.toml"
        dict_prof = load_dictionary(dict_path)

        artifacts = discover_artifacts(resolved_root, prof)
        tables = parse_project_tables(resolved_root, artifacts, adapter=prof.table_spec_adapter)
        findings = validate_dictionary_standards(tables, dict_prof)

        if format.lower() == "json":
            print(json.dumps([f.model_dump() for f in findings], indent=2))
        else:
            if not findings:
                print("Verdict: PASS (Data dictionary standards verified 100%)")
            else:
                print(f"Dictionary Audit Failures ({len(findings)}):")
                for f in findings:
                    print(f"  - [{f.code}] {f.message}")

        sys.exit(1 if findings else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def impact(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name for lineage search")],
    column: Annotated[Optional[str], typer.Option("--column", "-c", help="Target column name")] = None,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Analyzes downstream lineage and artifact impacts for a target table or column."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        impact_data = analyze_impact(resolved_root, artifacts, table, column)

        if format.lower() == "json":
            print(render_impact_json(impact_data))
        else:
            print(render_impact_text(impact_data))

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command("init-skill")
@app.command("install-skill")
def init_skill(
    agent: Annotated[AgentType, typer.Argument(help="Target agent type (gemini|codex|claude|all)")] = AgentType.ALL,
    project: Annotated[Optional[Path], typer.Option("--project", "-p", help="Install into project-local .skills directory")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing skill installation")] = False,
    symlink: Annotated[bool, typer.Option("--symlink", help="Create symlink instead of copying files")] = False,
) -> None:
    """Installs database-governance and database-migration-design skills for AI agent environments."""
    try:
        if project is not None:
            dest = install_skill_to_agent("project", project_root=project, overwrite=overwrite, symlink=symlink)
            print(f"Successfully installed skills to {dest}")
        else:
            if agent == AgentType.ALL:
                for target_agent in (AgentType.GEMINI, AgentType.CODEX, AgentType.CLAUDE):
                    dest = install_skill_to_agent(target_agent.value, overwrite=overwrite, symlink=symlink)
                    print(f"Successfully installed skills to {dest}")
            else:
                dest = install_skill_to_agent(agent.value, overwrite=overwrite, symlink=symlink)
                print(f"Successfully installed skills to {dest}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command("ddl-manage")
def ddl_manage(
    next_version: Annotated[bool, typer.Option("--next-version", help="Preview next migration version")] = False,
    create: Annotated[bool, typer.Option("--create", help="Create new empty migration file scaffold")] = False,
    slug: Annotated[Optional[str], typer.Option("--slug", help="Slug name for new migration file")] = None,
    series: Annotated[str, typer.Option("--series", help="Version series name (e.g. main, stg)")] = "main",
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Manages DDL migration version series and scaffolds empty migration files."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)

        if create:
            if not slug:
                raise GovernanceError("[DBG003] Slug name (--slug) is required when using --create.", exit_code=2)
            created_file = create_migration_file(resolved_root, prof, slug=slug, series_name=series)
            print(f"Successfully created migration file scaffold: {created_file.relative_to(resolved_root)}")
        else:
            ver_str, mig_dir = get_next_migration_version(resolved_root, prof, series_name=series)
            print(f"Next Migration Version: {ver_str} (Target Directory: {mig_dir.relative_to(resolved_root)})")

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def diff(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name for 1:1 schema diff")],
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Compares table markdown specification 1:1 against effective schema chain."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        tables = parse_project_tables(resolved_root, artifacts, adapter=prof.table_spec_adapter)
        doc_table = next(
            (t for t in tables if table.upper() == t.name.upper() or table.upper() in t.name.upper()), None
        )
        if not doc_table:
            raise GovernanceError(f"[DBG003] Table document for '{table}' not found.", exit_code=2)

        ddl_table = build_effective_schema(resolved_root, prof, table)
        findings = compare_table_specs(doc_table, ddl_table)

        if format.lower() == "json":
            print(json.dumps([f.model_dump() for f in findings], indent=2))
        else:
            print(render_diff_text(table, findings))

        sys.exit(1 if any(f.severity == Severity.ERROR for f in findings) else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command("migration-context")
def migration_context_cmd(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name for migration context")],
    base: Annotated[str, typer.Option("--base", help="Git base reference")] = "origin/main",
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Gathers structured migration context evidence for AI agent consumption."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        report = gather_migration_context(resolved_root, prof, table_name=table, base_ref=base)

        if format.lower() == "json":
            print(report.model_dump_json(indent=2))
        else:
            print(render_migration_context_text(report))

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@history_app.command("record")
def history_record_cmd(
    table: Annotated[Optional[str], typer.Option("--table", "-t", help="Target table name")] = None,
    staged: Annotated[bool, typer.Option("--staged", help="Infer semantic changes from staged git files")] = False,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write immutable JSON event file")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Previews or writes an immutable semantic history event JSON file."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)

        if write:
            check_report = run_audit_check(resolved_root, profile_path=profile)
            if check_report.documentation_state != "clean":
                raise GovernanceError(
                    f"[DBG402] Cannot record history event: contract check has error findings ({len(check_report.findings)}). Run 'dbg check' to resolve.",
                    exit_code=2,
                )

        event, written_path = record_history_event(resolved_root, prof, table_name=table, write=write)

        if not write:
            print("--- HISTORY EVENT PREVIEW (use --write to record) ---")
            print(event.model_dump_json(indent=2))
        else:
            if written_path:
                print(f"Successfully recorded history event to: {written_path.relative_to(resolved_root)}")

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@history_app.command("list")
def history_list_cmd(
    table: Annotated[Optional[str], typer.Option("--table", "-t", help="Filter history events by table")] = None,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Lists recorded history events in repository."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        events = list_history_events(resolved_root, prof, table_name=table)

        if format.lower() == "json":
            print(json.dumps([e.model_dump() for e in events], indent=2))
        else:
            if not events:
                print("No history events found.")
            else:
                print(f"Recorded History Events ({len(events)}):")
                for e in events:
                    print(f"  - [{e.event_id}] {e.recorded_at} | Table: {e.table} | Base: {e.base_commit}")

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@history_app.command("show")
def history_show_cmd(
    event_id: Annotated[str, typer.Argument(help="History Event ID (e.g. 01J...)")],
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Displays details of a specific history event."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        event = show_history_event(resolved_root, prof, event_id=event_id)
        print(event.model_dump_json(indent=2))
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@history_app.command("verify")
def history_verify_cmd(
    staged: Annotated[bool, typer.Option("--staged", help="Verify staged git changes")] = True,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Verifies that staged semantic DB changes have matching history events."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        findings = verify_history_events(resolved_root, prof, staged_only=staged)

        if not findings:
            print("Verdict: PASS (History event verification clean)")
        else:
            print(f"History Verification Failures ({len(findings)}):")
            for f in findings:
                print(f"  - [{f.code}] {f.message}")

        sys.exit(1 if findings else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def init(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    write: Annotated[bool, typer.Option("--write", "-w", help="Write profile TOML file")] = False,
) -> None:
    """Initializes a new .db-governance.toml profile configuration."""
    try:
        resolved_root = project.resolve()
        target_file = resolved_root / ".db-governance.toml"
        content = """version = 1
name = "default-project"

[[artifact_groups]]
name = "table-docs"
role = "source"
patterns = ["database/tables/*.md"]
required = true

[[artifact_groups]]
name = "ddl-migrations"
role = "migration"
patterns = ["database/migrations/V*.sql"]
required = true

[[artifact_groups]]
name = "changelog"
role = "history"
patterns = ["database/changelog.md"]
required = true

[[rules]]
id = "DBG-RULE-001"
description = "Table doc changes require migration and changelog updates."
when_changed_any = ["database/tables/*.md"]
applies_to = ["semantic", "unknown"]
severity = "error"

[[rules.require_changed]]
label = "DDL migration"
match_any = ["database/migrations/V*.sql"]

[[rules.require_changed]]
label = "change history"
match_any = ["database/changelog.md"]

[[migration_series]]
name = "main"
directory = "database/migrations"
file_pattern = "V1_{number}__{slug}.sql"
"""

        if not write:
            print("--- PROFILE INITIATION PREVIEW (use --write to save) ---")
            print(content)
        else:
            if target_file.exists():
                raise GovernanceError(f"[DBG401] Profile file already exists: {target_file}", exit_code=2)
            target_file.write_text(content, encoding="utf-8")
            print(f"Successfully initialized profile at: {target_file.relative_to(resolved_root)}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command("generate-spec")
def generate_spec_cmd(
    table: Annotated[str, typer.Option("--table", "-t", help="Table name")],
    columns: Annotated[Optional[str], typer.Option("--columns", "-c", help="Columns spec 'id:BIGINT,name:VARCHAR(100)'")] = None,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write scaffold files to disk")] = False,
) -> None:
    """Generates table markdown specification and migration scaffold files."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        parsed_cols = parse_column_args(columns)
        doc_text, ddl_text, written = generate_scaffold(resolved_root, prof, table, parsed_cols, write=write)

        if not write:
            print("--- TABLE SPEC SCAFFOLD (use --write to save) ---")
            print(doc_text)
        else:
            for p in written:
                print(f"Successfully generated scaffold: {p.relative_to(resolved_root)}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


"""Typer CLI interface for db-governance."""

from pathlib import Path
import sys
from typing import Annotated, Optional
import typer

<<<<<<< HEAD
=======
from db_governance.config import load_profile
>>>>>>> main
from db_governance.ddl_manage import create_migration_file, get_next_migration_version
from db_governance.dictionary import load_dictionary, validate_dictionary_standards
from db_governance.diff import build_effective_schema, compare_table_specs, render_diff_text
from db_governance.discovery import discover_artifacts
from db_governance.edit_spec import (
    add_column_to_doc,
    modify_column_in_doc,
    remove_column_from_doc,
)
from db_governance.errors import GovernanceError
from db_governance.git_changes import resolve_changed_files
from db_governance.impact import analyze_impact, render_impact_json, render_impact_text
from db_governance.models import AgentType, AuditReport, ChangeType, Finding, Severity
from db_governance.render import parse_project_tables, render_dbml, render_mermaid_erd
from db_governance.report import render_json, render_text, write_evidence
from db_governance.scaffold import generate_scaffold, parse_column_args
from db_governance.rules import evaluate_required_artifacts, evaluate_rules
from db_governance.runner import run_validators
from db_governance.templates import render_candidate_profile

app = typer.Typer(
    name="dbg",
    help="DB Governance CLI for contract synchronization, validator execution, and report generation.",
    no_args_is_help=True,
)


def _handle_error(exc: Exception) -> None:
    """Prints error message and exits with appropriate code."""
    if isinstance(exc, GovernanceError):
        print(f"Error: {exc.message}", file=sys.stderr)
        sys.exit(exc.exit_code)
    else:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)


def _build_audit_report(
    project: Path,
    profile_path: Optional[Path],
    base: Optional[str],
    changed_files_opt: Optional[list[Path]],
    change_type: ChangeType,
    run_validators_flag: bool,
    eval_rules: bool = True,
) -> AuditReport:
    resolved_root = project.resolve()
    target_prof_path, profile, prof_hash = load_profile(resolved_root, profile_path)
    artifacts = discover_artifacts(resolved_root, profile)

    findings: list[Finding] = []

    # Required artifact group check
    findings.extend(evaluate_required_artifacts(profile, artifacts))

    # Git / explicit changes
    changed_files = resolve_changed_files(resolved_root, base, changed_files_opt or [])

    if eval_rules:
        findings.extend(evaluate_rules(profile, changed_files, change_type))

    validators_results = []
    if run_validators_flag and profile.validators:
        val_results, val_findings = run_validators(resolved_root, profile.validators)
        validators_results.extend(val_results)
        findings.extend(val_findings)

    has_error_findings = any(f.severity == Severity.ERROR for f in findings)
    doc_state = "findings_detected" if has_error_findings else "clean"

    return AuditReport(
        schema_version=1,
        project_name=profile.name,
        project_root=str(resolved_root),
        profile_path=str(target_prof_path),
        profile_hash=prof_hash,
        change_type=change_type,
        changed_files=changed_files,
        artifacts=artifacts,
        findings=findings,
        validators=validators_results,
        documentation_state=doc_state,
        live_database_state="not_checked",
    )


@app.command()
def doctor(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Checks system environment, project path, and profile presence."""
    try:
        resolved_root = project.resolve()
        prof_path, profile, prof_hash = load_profile(resolved_root, None)
        artifacts = discover_artifacts(resolved_root, profile)

        report = AuditReport(
            schema_version=1,
            project_name=profile.name,
            project_root=str(resolved_root),
            profile_path=str(prof_path),
            profile_hash=prof_hash,
            change_type=ChangeType.UNKNOWN,
            changed_files=[],
            artifacts=artifacts,
            findings=[],
            validators=[],
            documentation_state="clean",
            live_database_state="not_checked",
        )

        if format.lower() == "json":
            print(render_json(report))
        else:
            print(render_text(report))

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def init(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    template: Annotated[Optional[Path], typer.Option("--template", "-t", help="External TOML template path")] = None,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write candidate profile to disk")] = False,
) -> None:
    """Initializes or previews candidate .db-governance.toml profile."""
    try:
        resolved_root = project.resolve()
        candidate = render_candidate_profile(resolved_root, template)

        if not write:
            print(candidate)
            sys.exit(0)

        target = (resolved_root / ".db-governance.toml").resolve()
        if target.exists():
            raise GovernanceError(
                "[DBG002] .db-governance.toml already exists. Refusing to overwrite.", exit_code=2
            )

        target.write_text(candidate, encoding="utf-8")
        print(f"Successfully created {target}")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def inspect(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Inventories matched and missing artifacts without evaluating change rules."""
    try:
        report = _build_audit_report(
            project=project,
            profile_path=profile,
            base=None,
            changed_files_opt=None,
            change_type=ChangeType.UNKNOWN,
            run_validators_flag=False,
            eval_rules=False,
        )

        if format.lower() == "json":
            print(render_json(report))
        else:
            print(render_text(report))

        has_errors = any(f.severity == Severity.ERROR for f in report.findings)
        sys.exit(1 if has_errors else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def check(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    base: Annotated[Optional[str], typer.Option("--base", "-b", help="Git base ref to compare against")] = None,
    changed_file: Annotated[
        Optional[list[Path]], typer.Option("--changed-file", help="Explicit changed file path")
    ] = None,
    change_type: Annotated[ChangeType, typer.Option("--change-type", help="Change classification")] = ChangeType.UNKNOWN,
    run_project_validators: Annotated[
        bool, typer.Option("--run-project-validators", help="Execute profile configured project validators")
    ] = False,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Evaluates synchronization rules and optional project validators."""
    try:
        report = _build_audit_report(
            project=project,
            profile_path=profile,
            base=base,
            changed_files_opt=changed_file,
            change_type=change_type,
            run_validators_flag=run_project_validators,
            eval_rules=True,
        )

        if format.lower() == "json":
            print(render_json(report))
        else:
            print(render_text(report))

        has_errors = any(f.severity == Severity.ERROR for f in report.findings)
        sys.exit(1 if has_errors else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def evidence(
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory for evidence bundle")],
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    base: Annotated[Optional[str], typer.Option("--base", "-b", help="Git base ref to compare against")] = None,
    changed_file: Annotated[
        Optional[list[Path]], typer.Option("--changed-file", help="Explicit changed file path")
    ] = None,
    change_type: Annotated[ChangeType, typer.Option("--change-type", help="Change classification")] = ChangeType.UNKNOWN,
    run_project_validators: Annotated[
        bool, typer.Option("--run-project-validators", help="Execute profile configured project validators")
    ] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing evidence files")] = False,
) -> None:
    """Evaluates synchronization rules and outputs evidence bundle (report.json & report.md)."""
    try:
        report = _build_audit_report(
            project=project,
            profile_path=profile,
            base=base,
            changed_files_opt=changed_file,
            change_type=change_type,
            run_validators_flag=run_project_validators,
            eval_rules=True,
        )

        write_evidence(report, output, overwrite=overwrite)
        print(f"Evidence bundle successfully written to {output.resolve()}")

        has_errors = any(f.severity == Severity.ERROR for f in report.findings)
        sys.exit(1 if has_errors else 0)
    except Exception as exc:
        _handle_error(exc)


def _do_install_skill(
    agent: AgentType,
    project: Optional[Path],
    target_dir: Optional[Path],
    symlink: bool,
    overwrite: bool,
) -> None:
    import shutil

    try:
        home = Path.home()
        dests: list[Path] = []

        if target_dir is not None:
            dests.append(target_dir.resolve())
        elif project is not None:
            dests.append((project.resolve() / ".skills" / "database-governance").resolve())
        else:
            if agent in (AgentType.GEMINI, AgentType.ALL):
                dests.append((home / ".gemini" / "config" / "skills" / "database-governance").resolve())
            if agent in (AgentType.CODEX, AgentType.ALL):
                dests.append((home / ".codex" / "skills" / "database-governance").resolve())
            if agent in (AgentType.CLAUDE, AgentType.ALL):
                dests.append((home / ".claude" / "skills" / "database-governance").resolve())

        # Locate skill directory in package resources or repo
        cand1 = (Path(__file__).parent / "skills" / "database-governance").resolve()
        cand2 = (Path(__file__).parent.parent.parent / "skills" / "database-governance").resolve()
        cand3 = (Path.cwd() / "skills" / "database-governance").resolve()

        src_skill = None
        for cand in [cand1, cand2, cand3]:
            if cand.exists() and (cand / "SKILL.md").exists():
                src_skill = cand
                break

        if src_skill is None:
            raise GovernanceError(
                f"[DBG001] Source skill directory not found in package resources ({cand1}) or repo ({cand2}).",
                exit_code=2,
            )

        for dest in dests:
            if dest.exists() and not overwrite:
                raise GovernanceError(
                    f"[DBG401] Skill destination directory '{dest}' already exists. Use --overwrite to replace.",
                    exit_code=2,
                )

            if dest.exists() or dest.is_symlink():
                if dest.is_symlink() or dest.is_file():
                    dest.unlink()
                else:
                    shutil.rmtree(dest)

            dest.parent.mkdir(parents=True, exist_ok=True)

            if symlink:
                dest.symlink_to(src_skill, target_is_directory=True)
                print(f"Successfully symlinked database-governance skill -> {dest}")
            else:
                shutil.copytree(src_skill, dest)
                print(f"Successfully installed database-governance skill to {dest}")

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command("install-skill")
def install_skill(
    agent: Annotated[
        AgentType, typer.Argument(help="Target AI agent environment (gemini|codex|claude|all)")
    ] = AgentType.GEMINI,
    project: Annotated[
        Optional[Path],
        typer.Option("--project", "-p", help="Install into project-local .skills/database-governance directory"),
    ] = None,
    target_dir: Annotated[
        Optional[Path],
        typer.Option("--target-dir", "-t", help="Explicit target skills directory path"),
    ] = None,
    symlink: Annotated[
        bool, typer.Option("--symlink", "-s", help="Create symlink instead of copying files")
    ] = False,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing skill directory")
    ] = False,
) -> None:
    """Installs database-governance skill into Antigravity/Codex/Claude agent or project-local directory."""
    _do_install_skill(agent, project, target_dir, symlink, overwrite)


@app.command("init-skill")
def init_skill(
    agent: Annotated[
        AgentType, typer.Argument(help="Target AI agent environment (gemini|codex|claude|all)")
    ] = AgentType.GEMINI,
    project: Annotated[
        Optional[Path],
        typer.Option("--project", "-p", help="Install into project-local .skills/database-governance directory"),
    ] = None,
    target_dir: Annotated[
        Optional[Path],
        typer.Option("--target-dir", "-t", help="Explicit target skills directory path"),
    ] = None,
    symlink: Annotated[
        bool, typer.Option("--symlink", "-s", help="Create symlink instead of copying files")
    ] = False,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing skill directory")
    ] = False,
) -> None:
    """Alias for install-skill. Initializes database-governance skill."""
    _do_install_skill(agent, project, target_dir, symlink, overwrite)



@app.command()
def render(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Diagram format (mermaid|dbml)")] = "mermaid",
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Renders Mermaid ERD or DBML diagram from discovered table specifications."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        tables = parse_project_tables(resolved_root, artifacts)

        fmt_lower = format.lower()
        if fmt_lower == "dbml":
            rendered = render_dbml(tables)
        else:
            rendered = render_mermaid_erd(tables)

        if output is None:
            print(rendered)
        else:
            out_path = output.resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered, encoding="utf-8")
            print(f"Diagram successfully written to {out_path}")

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def dictionary(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    dictionary: Annotated[
        Optional[Path], typer.Option("--dictionary", "-d", help="Explicit dictionary TOML path")
    ] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Validates discovered table specifications against data dictionary standards."""
    try:
        resolved_root = project.resolve()
        target_prof_path, prof, prof_hash = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        tables = parse_project_tables(resolved_root, artifacts)

        dict_path = dictionary or (resolved_root / ".db-dictionary.toml")
        if not dict_path.exists():
            findings = []
        else:
            dict_prof = load_dictionary(dict_path)
            findings = validate_dictionary_standards(tables, dict_prof)

        has_errors = any(f.severity == Severity.ERROR for f in findings)
        doc_state = "findings_detected" if has_errors else "clean"

        report = AuditReport(
            schema_version=1,
            project_name=prof.name,
            project_root=str(resolved_root),
            profile_path=str(target_prof_path),
            profile_hash=prof_hash,
            change_type=ChangeType.UNKNOWN,
            changed_files=[],
            artifacts=artifacts,
            findings=findings,
            validators=[],
            documentation_state=doc_state,
            live_database_state="not_checked",
        )

        if format.lower() == "json":
            print(render_json(report))
        else:
            print(render_text(report))

        sys.exit(1 if has_errors else 0)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def impact(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name for impact analysis")],
    column: Annotated[Optional[str], typer.Option("--column", "-c", help="Optional target column name")] = None,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text|json)")] = "text",
) -> None:
    """Analyzes downstream file dependencies and impact when a table or column changes."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        report = analyze_impact(resolved_root, artifacts, table=table, column=column)

        if format.lower() == "json":
            print(render_impact_json(report))
        else:
            print(render_impact_text(report))

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command("generate-spec")
def generate_spec(
    table: Annotated[str, typer.Option("--table", "-t", help="Table name to scaffold")],
    columns: Annotated[
        Optional[str], typer.Option("--columns", "-c", help="Columns spec (e.g. 'id:BIGINT,name:VARCHAR(100)')")
    ] = None,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write scaffold files to disk")] = False,
) -> None:
    """Generates table markdown specification and DDL migration template scaffolding."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)

        cols = parse_column_args(columns)
        doc_text, ddl_text, written = generate_scaffold(
            resolved_root, prof, table_name=table, columns=cols, write=write
        )

        if not write:
            print("==================================================")
            print(f"       TABLE SPEC SCAFFOLD ({table.upper()})       ")
            print("==================================================")
            print(doc_text)
            print("\n--------------------------------------------------")
            print("                DDL SQL SCAFFOLD                  ")
            print("--------------------------------------------------")
            print(ddl_text)
            print("==================================================")
        else:
            print("Successfully written scaffold files:")
            for p in written:
                print(f"  - {p}")

        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


edit_spec_app = typer.Typer(
    name="edit-spec",
    help="Edits existing table markdown specification documents directly via CLI.",
    no_args_is_help=True,
)
app.add_typer(edit_spec_app, name="edit-spec")


def _find_table_doc_path(project_root: Path, profile_path: Optional[Path], table_name: str) -> Path:
    target_prof_path, prof, _ = load_profile(project_root, profile_path)
    artifacts = discover_artifacts(project_root, prof)

    table_upper = table_name.upper()
    for group_name, path_list in artifacts.items():
        for rel_path in path_list:
            p = project_root / rel_path
            if p.stem.upper() == table_upper:
                return p

    raise GovernanceError(
        f"[DBG003] Table document for '{table_name}' not found in project artifacts.",
        exit_code=2,
    )


@edit_spec_app.command("add-column")
def edit_spec_add_column(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Column name to add")],
    type: Annotated[str, typer.Option("--type", help="Data type")],
    desc: Annotated[str, typer.Option("--desc", help="Column description")] = "",
    pk: Annotated[bool, typer.Option("--pk", help="Is primary key")] = False,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write changes to disk (default: dry-run)")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Appends a new column to markdown table spec (default is dry-run preview)."""
    try:
        resolved_root = project.resolve()
        doc_path = _find_table_doc_path(resolved_root, profile, table)
        out_text, written = add_column_to_doc(
            doc_path, col_name=name, col_type=type, col_desc=desc, is_pk=pk, write=write
        )
        if not written:
            print("--- DRY-RUN PREVIEW (use --write to save) ---")
            print(out_text)
        else:
            print(f"Successfully added column '{name}' to '{doc_path.relative_to(resolved_root)}'")
            print("Recommended next step: run 'dbg check' to verify contract synchronization.")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@edit_spec_app.command("modify-column")
def edit_spec_modify_column(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Column name to modify")],
    type: Annotated[Optional[str], typer.Option("--type", help="New data type")] = None,
    desc: Annotated[Optional[str], typer.Option("--desc", help="New column description")] = None,
    write: Annotated[bool, typer.Option("--write", "-w", help="Write changes to disk (default: dry-run)")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Modifies data type or description for an existing column in markdown table spec."""
    try:
        resolved_root = project.resolve()
        doc_path = _find_table_doc_path(resolved_root, profile, table)
        out_text, written = modify_column_in_doc(doc_path, col_name=name, col_type=type, col_desc=desc, write=write)
        if not written:
            print("--- DRY-RUN PREVIEW (use --write to save) ---")
            print(out_text)
        else:
            print(f"Successfully modified column '{name}' in '{doc_path.relative_to(resolved_root)}'")
            print("Recommended next step: run 'dbg check' to verify contract synchronization.")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@edit_spec_app.command("remove-column")
def edit_spec_remove_column(
    table: Annotated[str, typer.Option("--table", "-t", help="Target table name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Column name to remove")],
    write: Annotated[bool, typer.Option("--write", "-w", help="Write changes to disk (default: dry-run)")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm deletion when combined with --write")] = False,
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Removes an existing column from markdown table spec (requires --write --yes to save)."""
    try:
        resolved_root = project.resolve()
        doc_path = _find_table_doc_path(resolved_root, profile, table)
        out_text, written = remove_column_from_doc(doc_path, col_name=name, write=write, yes=yes)
        if not written:
            print("--- DRY-RUN PREVIEW (use --write --yes to save) ---")
            print(out_text)
        else:
            print(f"Successfully removed column '{name}' from '{doc_path.relative_to(resolved_root)}'")
            print("Recommended next step: run 'dbg check' to verify contract synchronization.")
        sys.exit(0)
    except Exception as exc:
        _handle_error(exc)


@app.command("ddl-manage")
def ddl_manage(
    next_version: Annotated[bool, typer.Option("--next-version", help="Preview next migration version")] = False,
    create: Annotated[bool, typer.Option("--create", help="Create new migration file scaffold")] = False,
    slug: Annotated[Optional[str], typer.Option("--slug", help="Slug name for new migration file")] = None,
    series: Annotated[str, typer.Option("--series", help="Version series (main|stg)")] = "main",
    project: Annotated[Path, typer.Option("--project", "-p", help="Project root directory")] = Path("."),
    profile: Annotated[Optional[Path], typer.Option("--profile", help="Explicit profile path")] = None,
) -> None:
    """Manages DDL migration version series and scaffolds new migration files."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)

        if create:
            if not slug:
                raise GovernanceError("[DBG003] Slug name (--slug) is required when using --create.", exit_code=2)
            created_file = create_migration_file(resolved_root, prof, slug=slug, series_name=series)
            print(f"Successfully created migration file: {created_file.relative_to(resolved_root)}")
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
    """Compares table markdown specification 1:1 against effective DDL schema chain."""
    try:
        resolved_root = project.resolve()
        _, prof, _ = load_profile(resolved_root, profile)
        artifacts = discover_artifacts(resolved_root, prof)

        tables = parse_project_tables(resolved_root, artifacts)
        doc_table = next((t for t in tables if t.name.upper() == table.upper()), None)
        if not doc_table:
            raise GovernanceError(f"[DBG003] Table document for '{table}' not found.", exit_code=2)

        ddl_table = build_effective_schema(resolved_root, prof, table)
        findings = compare_table_specs(doc_table, ddl_table)

        if format.lower() == "json":
            import json

            print(json.dumps([f.model_dump() for f in findings], indent=2))
        else:
            print(render_diff_text(table, findings))

        sys.exit(1 if any(f.severity == Severity.ERROR for f in findings) else 0)
    except Exception as exc:
        _handle_error(exc)









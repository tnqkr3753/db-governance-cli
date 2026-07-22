"""Typer CLI interface for db-governance."""

from pathlib import Path
import sys
from typing import Annotated, Optional
import typer

from db_governance.config import load_profile
from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError
from db_governance.git_changes import resolve_changed_files
from db_governance.models import AuditReport, ChangeType, Finding, Severity
from db_governance.report import render_json, render_text, write_evidence
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


@app.command("install-skill")
def install_skill(
    target_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--target-dir",
            "-t",
            help="Target skills directory (defaults to ~/.gemini/config/skills/database-governance)",
        ),
    ] = None,
    symlink: Annotated[
        bool, typer.Option("--symlink", "-s", help="Create symlink instead of copying files")
    ] = False,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing skill directory")
    ] = False,
) -> None:
    """Installs the database-governance skill into Antigravity skill configuration directory."""
    import shutil

    try:
        if target_dir is None:
            dest = (Path.home() / ".gemini" / "config" / "skills" / "database-governance").resolve()
        else:
            dest = target_dir.resolve()

        if dest.exists() and not overwrite:
            raise GovernanceError(
                f"[DBG401] Skill destination directory '{dest}' already exists. Use --overwrite to replace.",
                exit_code=2,
            )

        # Locate skill directory in repo or package
        src_skill = (Path(__file__).parent.parent.parent / "skills" / "database-governance").resolve()
        if not src_skill.exists():
            raise GovernanceError(
                f"[DBG001] Source skill directory not found at {src_skill}", exit_code=2
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


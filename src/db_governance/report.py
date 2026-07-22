"""Report rendering and atomic evidence file writing."""

import os
from pathlib import Path
import uuid

from db_governance.errors import GovernanceError
from db_governance.models import AuditReport


def render_text(report: AuditReport) -> str:
    """Renders human-readable text audit report."""
    lines: list[str] = [
        "==================================================",
        "          DATABASE GOVERNANCE REPORT              ",
        "==================================================",
        f"Project Name        : {report.project_name}",
        f"Project Root        : {report.project_root}",
        f"Profile Path        : {report.profile_path}",
        f"Profile Hash        : {report.profile_hash}",
        f"Change Type         : {report.change_type}",
        "--------------------------------------------------",
        f"Documentation State : {report.documentation_state}",
        f"Live Database State : {report.live_database_state}",
        "--------------------------------------------------",
        f"Verdict             : {'PASS' if report.documentation_state == 'clean' else 'FAIL'}",
        "--------------------------------------------------",
        "Changed Files:",
    ]
    if report.changed_files:
        for cf in report.changed_files:
            lines.append(f"  - {cf}")
    else:
        lines.append("  (none)")

    lines.append("--------------------------------------------------")
    lines.append(f"Findings ({len(report.findings)}):")
    if report.findings:
        for f in report.findings:
            paths_str = f" [{', '.join(f.paths)}]" if f.paths else ""
            lines.append(f"  - [{f.severity.upper()}] {f.code}: {f.message}{paths_str}")
    else:
        lines.append("  (no findings)")

    lines.append("--------------------------------------------------")
    lines.append(f"Validators ({len(report.validators)}):")
    if report.validators:
        for v in report.validators:
            status = "PASS" if v.exit_code == 0 else f"FAIL (exit {v.exit_code})"
            lines.append(f"  - {v.name}: {status} ({v.duration_ms}ms)")
    else:
        lines.append("  (no validators executed)")

    lines.append("==================================================")
    return "\n".join(lines)


def render_json(report: AuditReport) -> str:
    """Renders AuditReport as formatted JSON string."""
    return report.model_dump_json(indent=2)


def render_markdown(report: AuditReport) -> str:
    """Renders AuditReport as Markdown document."""
    lines: list[str] = [
        f"# Database Governance Report: {report.project_name}",
        "",
        "## Summary",
        f"- **Project Root**: `{report.project_root}`",
        f"- **Profile Path**: `{report.profile_path}`",
        f"- **Profile Hash**: `{report.profile_hash}`",
        f"- **Change Type**: `{report.change_type}`",
        "",
        "## Verdict",
        f"**{'PASS' if report.documentation_state == 'clean' else 'FAIL'}**",
        "",
        "## Documentation State",
        f"`{report.documentation_state}`",
        "",
        "## Live Database State",
        f"`{report.live_database_state}`",
        "",
        "## Changed Files",
    ]
    if report.changed_files:
        for cf in report.changed_files:
            lines.append(f"- `{cf}`")
    else:
        lines.append("*None*")

    lines.extend(["", "## Findings"])
    if report.findings:
        for f in report.findings:
            lines.append(f"- **[{f.severity.upper()}] {f.code}**: {f.message}")
            if f.paths:
                lines.append(f"  - Paths: `{', '.join(f.paths)}`")
    else:
        lines.append("*No findings detected.*")

    lines.extend(["", "## Validators"])
    if report.validators:
        for v in report.validators:
            lines.append(f"### {v.name}")
            lines.append(f"- **Exit Code**: `{v.exit_code}`")
            lines.append(f"- **Duration**: `{v.duration_ms}ms`")
            if v.stdout:
                lines.append("```\n" + v.stdout + "\n```")
            if v.stderr:
                lines.append("```stderr\n" + v.stderr + "\n```")
    else:
        lines.append("*No validators executed.*")

    return "\n".join(lines)


def write_evidence(
    report: AuditReport, output_dir: Path, overwrite: bool = False
) -> None:
    """Writes report.json and report.md atomically into output_dir.

    Args:
        report: AuditReport instance.
        output_dir: Destination directory.
        overwrite: If False, raises error if target files exist.

    Raises:
        GovernanceError: If files exist and overwrite is False (DBG401).
    """
    resolved_dir = output_dir.resolve()
    target_json = resolved_dir / "report.json"
    target_md = resolved_dir / "report.md"

    if not overwrite and (target_json.exists() or target_md.exists()):
        raise GovernanceError(
            f"[DBG401] Evidence destination '{output_dir}' already exists. Use --overwrite to replace.",
            exit_code=2,
        )

    resolved_dir.mkdir(parents=True, exist_ok=True)

    json_content = render_json(report)
    md_content = render_markdown(report)

    # Write atomically using a temporary subdirectory inside output_dir
    tmp_sub = resolved_dir / f".tmp_{uuid.uuid4().hex}"
    tmp_sub.mkdir()

    tmp_json = tmp_sub / "report.json"
    tmp_md = tmp_sub / "report.md"

    tmp_json.write_text(json_content, encoding="utf-8")
    tmp_md.write_text(md_content, encoding="utf-8")

    # Atomically replace files
    os.replace(tmp_json, target_json)
    os.replace(tmp_md, target_md)

    # Clean up temp dir
    try:
        tmp_sub.rmdir()
    except OSError:
        pass

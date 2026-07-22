"""Report rendering and atomic evidence file writing."""

import os
from pathlib import Path
import uuid

from db_governance.errors import GovernanceError
from db_governance.models import AuditReport


def render_text(report: AuditReport) -> str:
    """Renders concise, token-efficient text audit report."""
    verdict = "PASS" if report.documentation_state == "clean" else "FAIL"

    if verdict == "PASS" and not report.findings:
        val_summary = f", {len(report.validators)} validator(s) passed" if report.validators else ""
        return f"Verdict: PASS (project: {report.project_name}, doc state: clean{val_summary})"

    lines: list[str] = [
        f"Verdict: FAIL (project: {report.project_name}, findings: {len(report.findings)})",
        "Findings:",
    ]
    for f in report.findings:
        paths_str = f" [{', '.join(f.paths)}]" if f.paths else ""
        lines.append(f"  - [{f.code}] {f.severity.upper()}: {f.message}{paths_str}")

    if report.validators:
        lines.append("Validators:")
        for v in report.validators:
            if v.exit_code != 0:
                lines.append(f"  - [{v.name}] FAIL (exit {v.exit_code}, {v.duration_ms}ms)")

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

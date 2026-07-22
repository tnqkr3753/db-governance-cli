"""Impact and cross-reference lineage analysis module."""

from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field


class ImpactMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_name: str
    path: str
    line_number: int
    line_content: str


class ImpactReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_table: str
    target_column: str | None = None
    total_impacted_files: int = 0
    matches: list[ImpactMatch] = Field(default_factory=list)


def analyze_impact(
    project_root: Path,
    artifacts: dict[str, list[str]],
    table: str,
    column: str | None = None,
) -> ImpactReport:
    """Analyzes cross-reference dependencies for a table or column across artifacts.

    Args:
        project_root: Resolved path to project root.
        artifacts: Dictionary mapping group name to list of relative paths.
        table: Target table name.
        column: Optional target column name.

    Returns:
        ImpactReport detailing matched files, lines, and contents.
    """
    resolved_root = project_root.resolve()
    matches: list[ImpactMatch] = []
    impacted_files: set[str] = set()

    table_upper = table.upper()
    col_upper = column.upper() if column else None

    for group_name, path_list in artifacts.items():
        for rel_path in path_list:
            full_path = resolved_root / rel_path
            if not full_path.exists() or not full_path.is_file():
                continue

            try:
                lines = full_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue

            for idx, line in enumerate(lines, start=1):
                line_upper = line.upper()
                table_matched = table_upper in line_upper

                if col_upper:
                    column_matched = col_upper in line_upper
                    matched = table_matched or column_matched
                else:
                    matched = table_matched

                if matched:
                    matches.append(
                        ImpactMatch(
                            group_name=group_name,
                            path=rel_path,
                            line_number=idx,
                            line_content=line.strip(),
                        )
                    )
                    impacted_files.add(rel_path)

    return ImpactReport(
        target_table=table,
        target_column=column,
        total_impacted_files=len(impacted_files),
        matches=matches,
    )


def render_impact_text(report: ImpactReport) -> str:
    """Renders ImpactReport as formatted text."""
    lines: list[str] = [
        "==================================================",
        "             IMPACT ANALYSIS REPORT               ",
        "==================================================",
        f"Target Table        : {report.target_table}",
        f"Target Column       : {report.target_column or '(all)'}",
        f"Impacted Files Count: {report.total_impacted_files}",
        "--------------------------------------------------",
        "Impacted Occurrences:",
    ]

    if report.matches:
        for m in report.matches:
            lines.append(f"  - [{m.group_name}] {m.path}:{m.line_number} -> {m.line_content}")
    else:
        lines.append("  (no references found)")

    lines.append("==================================================")
    return "\n".join(lines)


def render_impact_json(report: ImpactReport) -> str:
    """Renders ImpactReport as JSON string."""
    return report.model_dump_json(indent=2)

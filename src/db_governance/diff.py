"""Baseline + Migration chain schema parity inspector module (dbg diff)."""

import re
from pathlib import Path

from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError
from db_governance.models import ArtifactRole, Finding, ProjectProfile, Severity
from db_governance.render import ColumnSpec, TableSpec, parse_project_tables


def _parse_sql_columns_from_statement(sql: str, table_name: str) -> list[ColumnSpec]:
    """Parses CREATE TABLE statement for table_name into ColumnSpec list."""
    table_upper = table_name.upper()
    pattern = re.compile(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[^\.\s]+\.)?([^\.\s\(\)]+)\s*\((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )

    columns: list[ColumnSpec] = []
    for match in pattern.finditer(sql):
        tname = match.group(1).strip("`\"'").upper()
        if tname != table_upper:
            continue

        body = match.group(2)
        # Split by comma outside parentheses
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        for line in lines:
            line_clean = line.rstrip(",")
            if (
                line_clean.upper().startswith("PRIMARY KEY")
                or line_clean.upper().startswith("FOREIGN KEY")
                or line_clean.upper().startswith("CONSTRAINT")
            ):
                continue

            parts = line_clean.split(maxsplit=2)
            if len(parts) >= 2:
                col_name = parts[0].strip("`\"'")
                col_type = parts[1].upper()
                rest = parts[2].upper() if len(parts) >= 3 else ""
                is_pk = "PRIMARY KEY" in rest
                is_null = "NOT NULL" not in rest
                columns.append(
                    ColumnSpec(name=col_name, data_type=col_type, is_pk=is_pk, is_nullable=is_null)
                )
    return columns


def build_effective_schema(
    project_root: Path,
    profile: ProjectProfile,
    table_name: str,
) -> TableSpec:
    """Builds effective schema for table_name by applying ordered migration SQL chain."""
    resolved_root = project_root.resolve()
    artifacts = discover_artifacts(resolved_root, profile)

    mig_files: list[Path] = []
    for group in profile.artifact_groups:
        if group.role == ArtifactRole.MIGRATION:
            for rel_p in artifacts.get(group.name, []):
                p = resolved_root / rel_p
                if p.suffix.lower() == ".sql":
                    mig_files.append(p)

    mig_files.sort(key=lambda p: p.name)

    table_upper = table_name.upper()
    cols_dict: dict[str, ColumnSpec] = {}

    for f in mig_files:
        try:
            sql_content = f.read_text(encoding="utf-8")
        except Exception:
            continue

        # Process CREATE TABLE
        parsed_cols = _parse_sql_columns_from_statement(sql_content, table_name)
        for c in parsed_cols:
            cols_dict[c.name.upper()] = c

        # Process ALTER TABLE ADD COLUMN
        alter_pattern = re.compile(
            rf"ALTER\s+TABLE\s+(?:[^\.\s]+\.)?([^\.\s\(\)]+)\s+ADD\s+(?:COLUMN\s+)?([^\s]+)\s+([^\s;,]+)",
            re.IGNORECASE,
        )
        for match in alter_pattern.finditer(sql_content):
            tname = match.group(1).strip("`\"'").upper()
            if tname == table_upper:
                col_name = match.group(2).strip("`\"'")
                col_type = match.group(3).upper()
                cols_dict[col_name.upper()] = ColumnSpec(name=col_name, data_type=col_type)

    return TableSpec(name=table_upper, columns=list(cols_dict.values()))


def compare_table_specs(doc_table: TableSpec, ddl_table: TableSpec) -> list[Finding]:
    """Compares Markdown document TableSpec against Effective DDL TableSpec."""
    findings: list[Finding] = []

    doc_cols = {c.name.upper(): c for c in doc_table.columns}
    ddl_cols = {c.name.upper(): c for c in ddl_table.columns}

    # Check missing in DDL
    for name, c in doc_cols.items():
        if name not in ddl_cols:
            findings.append(
                Finding(
                    code="DBG203",
                    severity=Severity.ERROR,
                    message=f"Table '{doc_table.name}': column '{name}' defined in doc but missing in effective DDL schema.",
                    paths=[],
                )
            )
        else:
            ddl_c = ddl_cols[name]
            # Check type mismatch
            doc_type_clean = c.data_type.upper().replace(" ", "")
            ddl_type_clean = ddl_c.data_type.upper().replace(" ", "")
            if doc_type_clean != ddl_type_clean:
                findings.append(
                    Finding(
                        code="DBG204",
                        severity=Severity.ERROR,
                        message=f"Table '{doc_table.name}': column '{name}' type mismatch (doc: '{c.data_type}', DDL: '{ddl_c.data_type}').",
                        paths=[],
                    )
                )

    # Check missing in doc
    for name in ddl_cols:
        if name not in doc_cols:
            findings.append(
                Finding(
                    code="DBG203",
                    severity=Severity.ERROR,
                    message=f"Table '{doc_table.name}': column '{name}' defined in effective DDL schema but missing in table doc.",
                    paths=[],
                )
            )

    return findings


def render_diff_text(target_table: str, findings: list[Finding]) -> str:
    """Renders diff audit findings as formatted text."""
    lines = [
        "==================================================",
        "             SCHEMA DIFF AUDIT REPORT             ",
        "==================================================",
        f"Target Table : {target_table.upper()}",
        f"Total Findings: {len(findings)}",
        "--------------------------------------------------",
    ]
    if not findings:
        lines.append("  Verdict: CLEAN (Doc and DDL schemas match 100%)")
    else:
        for f in findings:
            lines.append(f"  - [{f.code}] ({f.severity.upper()}) {f.message}")
    lines.append("==================================================")
    return "\n".join(lines)

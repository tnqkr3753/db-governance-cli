"""ERD and DBML diagram rendering module."""

from pathlib import Path
import re
from pydantic import BaseModel, ConfigDict, Field


class ColumnSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    data_type: str = "VARCHAR"
    is_pk: bool = False
    is_nullable: bool = True
    description: str = ""


class TableSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    columns: list[ColumnSpec] = Field(default_factory=list)


def parse_markdown_table_spec(text: str, default_name: str) -> TableSpec:
    """Parses markdown table specification text into TableSpec."""
    table_name = default_name
    lines = text.splitlines()
    for line in lines:
        if line.startswith("#"):
            match = re.search(r"#\s*([A-Za-z0-9_]+)", line)
            if match:
                table_name = match.group(1)
                break

    columns: list[ColumnSpec] = []
    for line in lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 2:
                col_name = parts[0]
                col_type = parts[1]
                if col_name.startswith("-") or col_name.lower() in ("column", "컬럼명", "컬럼", "field"):
                    continue

                if col_name:
                    is_pk = "PK" in col_type.upper() or "PRIMARY" in col_type.upper() or col_name.lower() == "id"
                    clean_type = col_type.replace("PK", "").strip() or "VARCHAR"
                    desc = parts[2] if len(parts) >= 3 else ""
                    columns.append(
                        ColumnSpec(
                            name=col_name,
                            data_type=clean_type,
                            is_pk=is_pk,
                            is_nullable=not is_pk,
                            description=desc,
                        )
                    )

    return TableSpec(name=table_name, columns=columns)


def parse_project_tables(project_root: Path, artifacts: dict[str, list[str]]) -> list[TableSpec]:
    """Parses discovered table doc artifacts into list of TableSpecs."""
    tables: list[TableSpec] = []
    table_docs = artifacts.get("table-docs", [])
    for rel_path in table_docs:
        full_path = project_root / rel_path
        if full_path.exists() and full_path.is_file():
            text = full_path.read_text(encoding="utf-8")
            default_name = full_path.stem
            spec = parse_markdown_table_spec(text, default_name)
            tables.append(spec)
    return tables


def render_mermaid_erd(tables: list[TableSpec]) -> str:
    """Renders TableSpecs as Mermaid erDiagram markdown block."""
    lines = ["erDiagram"]
    for t in tables:
        lines.append(f"    {t.name} {{")
        for c in t.columns:
            pk_str = " PK" if c.is_pk else ""
            lines.append(f"        {c.data_type} {c.name}{pk_str}")
        lines.append("    }")
    return "\n".join(lines)


def render_dbml(tables: list[TableSpec]) -> str:
    """Renders TableSpecs as DBML code block."""
    lines = []
    for t in tables:
        lines.append(f"Table {t.name} {{")
        for c in t.columns:
            pk_str = " [pk]" if c.is_pk else ""
            lines.append(f"    {c.name} {c.data_type}{pk_str}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)

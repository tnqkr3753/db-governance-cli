"""ERD and DBML diagram rendering module."""

from pathlib import Path
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
        if line.startswith("# "):
            raw_name = line.replace("#", "").strip().strip("`\"'")
            first_token = raw_name.split()[0] if raw_name.split() else raw_name
            table_name = first_token.split(".")[-1] if "." in first_token else first_token
            break

    columns: list[ColumnSpec] = []
    in_col_table = False
    name_idx = 0
    type_idx = 1
    pk_idx: int | None = None
    desc_idx: int | None = None

    for line in lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 2:
                row_str = " ".join(parts).lower()
                if any(h in row_str for h in ["column", "컬럼", "field"]) and any(
                    t in row_str for t in ["type", "타입", "data"]
                ):
                    in_col_table = True
                    for idx, p in enumerate(parts):
                        p_low = p.lower()
                        if p_low in ("컬럼명", "컬럼", "column", "field", "name"):
                            name_idx = idx
                        elif p_low in ("타입", "type", "datatype", "data_type"):
                            type_idx = idx
                        elif "pk" in p_low or "primary" in p_low:
                            pk_idx = idx
                        elif "설명" in p_low or "description" in p_low or "desc" in p_low:
                            desc_idx = idx
                    continue

                if "---" in row_str:
                    continue

                if in_col_table:
                    if len(parts) <= max(name_idx, type_idx):
                        continue

                    col_name = parts[name_idx].strip("`\"'")
                    col_type = parts[type_idx].strip("`\"'")
                    if col_name and not col_name.isdigit() and col_name.lower() not in ("컬럼명", "컬럼", "column", "field", "name", "no"):
                        is_pk = (
                            (pk_idx is not None and len(parts) > pk_idx and "Y" in parts[pk_idx].upper())
                            or "PK" in col_type.upper()
                            or "PRIMARY" in col_type.upper()
                            or col_name.lower() == "id"
                        )
                        clean_type = col_type.replace("[PK]", "").replace("PK", "").strip() or "VARCHAR"
                        desc = parts[desc_idx] if desc_idx is not None and len(parts) > desc_idx else ""
                        columns.append(
                            ColumnSpec(
                                name=col_name,
                                data_type=clean_type,
                                is_pk=is_pk,
                                is_nullable=not is_pk,
                                description=desc,
                            )
                        )
        else:
            if in_col_table and line.strip() == "":
                in_col_table = False

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

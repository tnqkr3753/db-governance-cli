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
            parts_low = [p.lower() for p in parts]
            if len(parts) >= 2:
                has_col_header = any(any(h in p for h in ["컬럼명", "컬럼", "column", "field", "name"]) for p in parts_low)
                has_type_header = any(any(t in p for t in ["타입", "type", "datatype", "data_type"]) for p in parts_low)

                if has_col_header and has_type_header:
                    in_col_table = True
                    name_idx = None
                    type_idx = None
                    pk_idx = None
                    desc_idx = None

                    for idx, p in enumerate(parts_low):
                        if name_idx is None and p in ("컬럼명", "컬럼", "column", "field", "name"):
                            name_idx = idx
                        elif type_idx is None and any(t in p for t in ["데이터 타입", "데이터타입", "타입", "type", "datatype", "data_type"]):
                            type_idx = idx
                        elif pk_idx is None and ("pk" in p or "primary" in p):
                            pk_idx = idx
                        elif desc_idx is None and ("설명" in p or "description" in p or "desc" in p):
                            desc_idx = idx

                    if name_idx is None:
                        for idx, p in enumerate(parts_low):
                            if "컬럼" in p and "한글" not in p:
                                name_idx = idx
                                break

                    name_idx = name_idx if name_idx is not None else 0
                    type_idx = type_idx if type_idx is not None else 1
                    continue

                row_str = " ".join(parts).lower()
                if "---" in row_str:
                    continue

                if in_col_table:
                    if len(parts) <= max(name_idx, type_idx):
                        continue

                    col_name = parts[name_idx].strip("`\"'").upper()
                    col_type = parts[type_idx].strip("`\"'")
                    if col_name and not col_name.isdigit():
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

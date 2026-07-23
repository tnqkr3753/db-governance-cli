"""Markdown table specification parsing and rendering module."""

from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from db_governance.models import TableSpecAdapterSpec


class ColumnSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    data_type: str
    is_pk: bool = False
    is_nullable: bool = True
    description: str = ""


class TableSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    columns: list[ColumnSpec] = Field(default_factory=list)


def parse_markdown_table_spec(
    text: str, default_name: str, adapter: TableSpecAdapterSpec | None = None
) -> TableSpec:
    """Parses markdown table specification text into TableSpec using optional adapter configuration."""
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
    name_idx = None
    type_idx = None
    pk_idx = None
    desc_idx = None
    null_idx = None

    col_header = adapter.name_header.lower() if adapter else "컬럼명"
    type_header = adapter.type_header.lower() if adapter else "데이터 타입"
    null_header = adapter.nullable_header.lower() if adapter else "null"
    pk_header = adapter.primary_key_header.lower() if adapter else "pk"
    desc_header = adapter.description_header.lower() if adapter else "설명"

    for line in lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            parts_low = [p.lower() for p in parts]
            if len(parts) >= 2:
                has_col_header = any(col_header in p for p in parts_low) or any(
                    any(h in p for h in ["컬럼명", "컬럼", "column", "field", "name"]) for p in parts_low
                )
                has_type_header = any(type_header in p for p in parts_low) or any(
                    any(t in p for t in ["데이터 타입", "데이터타입", "타입", "type", "datatype", "data_type"])
                    for p in parts_low
                )

                if has_col_header and has_type_header:
                    in_col_table = True
                    name_idx = None
                    type_idx = None
                    pk_idx = None
                    desc_idx = None
                    null_idx = None

                    for idx, p in enumerate(parts_low):
                        if name_idx is None and col_header in p:
                            name_idx = idx
                        elif type_idx is None and type_header in p:
                            type_idx = idx
                        elif pk_idx is None and pk_header in p:
                            pk_idx = idx
                        elif null_idx is None and null_header in p:
                            null_idx = idx
                        elif desc_idx is None and desc_header in p:
                            desc_idx = idx

                    # Fallback index resolution if adapter didn't match exactly
                    if name_idx is None:
                        for idx, p in enumerate(parts_low):
                            if p in ("컬럼명", "컬럼", "column", "field", "name") or ("컬럼" in p and "한글" not in p):
                                name_idx = idx
                                break
                    if type_idx is None:
                        for idx, p in enumerate(parts_low):
                            if any(t in p for t in ["데이터 타입", "데이터타입", "타입", "type", "datatype", "data_type"]):
                                type_idx = idx
                                break

                    name_idx = name_idx if name_idx is not None else 0
                    type_idx = type_idx if type_idx is not None else 1
                    continue

                row_str = " ".join(parts).lower()
                if "---" in row_str:
                    continue

                if in_col_table:
                    idx_n = name_idx if name_idx is not None else 0
                    idx_t = type_idx if type_idx is not None else 1
                    if len(parts) <= max(idx_n, idx_t):
                        continue

                    col_name = parts[idx_n].strip("`\"'").upper()
                    col_type = parts[idx_t].strip("`\"'")
                    if col_name and not col_name.isdigit():
                        is_pk = (
                            (pk_idx is not None and len(parts) > pk_idx and "Y" in parts[pk_idx].upper())
                            or "PK" in col_type.upper()
                            or "PRIMARY" in col_type.upper()
                            or col_name.lower() == "id"
                        )

                        is_null = True
                        if null_idx is not None and len(parts) > null_idx:
                            null_val = parts[null_idx].upper().strip()
                            if null_val in ("N", "NOT NULL", "FALSE"):
                                is_null = False

                        clean_type = col_type.replace("[PK]", "").replace("PK", "").strip() or "VARCHAR"
                        desc = parts[desc_idx] if desc_idx is not None and len(parts) > desc_idx else ""
                        columns.append(
                            ColumnSpec(
                                name=col_name,
                                data_type=clean_type,
                                is_pk=is_pk,
                                is_nullable=not is_pk if is_pk else is_null,
                                description=desc,
                            )
                        )
        else:
            if in_col_table and line.strip() == "":
                in_col_table = False

    return TableSpec(name=table_name, columns=columns)


def parse_project_tables(
    project_root: Path, artifacts: dict[str, list[str]], adapter: TableSpecAdapterSpec | None = None
) -> list[TableSpec]:
    """Parses all table spec files in project source artifacts into TableSpec objects."""
    tables: list[TableSpec] = []
    for group_name, path_list in artifacts.items():
        for rel_path in path_list:
            if rel_path.endswith(".md"):
                full_path = project_root / rel_path
                if full_path.exists():
                    try:
                        content = full_path.read_text(encoding="utf-8")
                        spec = parse_markdown_table_spec(content, default_name=full_path.stem, adapter=adapter)
                        if spec.columns:
                            tables.append(spec)
                    except Exception:
                        continue
    return tables


def render_mermaid_erd(tables: list[TableSpec]) -> str:
    """Renders Mermaid ERD text block from TableSpec list."""
    lines = ["erDiagram"]
    for t in tables:
        lines.append(f"    {t.name} {{")
        for c in t.columns:
            pk_str = " PK" if c.is_pk else ""
            lines.append(f"        {c.data_type} {c.name}{pk_str}")
        lines.append("    }")
    return "\n".join(lines)


def render_dbml(tables: list[TableSpec]) -> str:
    """Renders DBML schema text block from TableSpec list."""
    lines = []
    for t in tables:
        lines.append(f"Table {t.name} {{")
        for c in t.columns:
            opts: list[str] = []
            if c.is_pk:
                opts.append("pk")
            elif not c.is_nullable:
                opts.append("not null")
            if c.description:
                opts.append(f"note: '{c.description}'")
            opt_str = f" [{', '.join(opts)}]" if opts else ""
            lines.append(f"  {c.name} {c.data_type}{opt_str}")
        lines.append("}\n")
    return "\n".join(lines)

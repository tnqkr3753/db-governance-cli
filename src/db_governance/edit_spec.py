"""Markdown table specification editor module."""

from pathlib import Path
from db_governance.errors import GovernanceError


def _parse_table_row(line: str) -> list[str] | None:
    """Parses a markdown table row '| col | type | desc |' into list of column values."""
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    parts = [p.strip() for p in line.split("|")[1:-1]]
    return parts


def add_column_to_doc(
    doc_path: Path,
    col_name: str,
    col_type: str,
    col_desc: str = "",
    is_pk: bool = False,
    is_nullable: bool = True,
    write: bool = False,
) -> tuple[str, bool]:
    """Appends a new column row to the markdown table in doc_path.

    Returns:
        Tuple of (rendered markdown text, whether changes were written to file).
    """
    if not doc_path.exists():
        raise GovernanceError(f"[DBG003] Target document file '{doc_path}' does not exist.", exit_code=2)

    lines = doc_path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    in_table = False
    added = False

    pk_note = " [PK]" if is_pk else ""
    type_str = f"{col_type}{pk_note}"
    new_row = f"| {col_name} | {type_str} | {col_desc} |"

    for idx, line in enumerate(lines):
        new_lines.append(line)
        row = _parse_table_row(line)
        if row and len(row) >= 2:
            if "---" in row[0] or "---" in row[1]:
                in_table = True
                continue

        if in_table:
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            next_row = _parse_table_row(next_line)
            if not next_row and not added:
                new_lines.append(new_row)
                added = True
                in_table = False

    if not added:
        new_lines.append(new_row)

    out_text = "\n".join(new_lines) + "\n"
    if write:
        doc_path.write_text(out_text, encoding="utf-8")
    return out_text, write


def modify_column_in_doc(
    doc_path: Path,
    col_name: str,
    col_type: str | None = None,
    col_desc: str | None = None,
    write: bool = False,
) -> tuple[str, bool]:
    """Modifies data type or description for an existing column in doc_path."""
    if not doc_path.exists():
        raise GovernanceError(f"[DBG003] Target document file '{doc_path}' does not exist.", exit_code=2)

    lines = doc_path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    col_upper = col_name.upper()
    modified = False

    for line in lines:
        row = _parse_table_row(line)
        if row and len(row) >= 2 and "---" not in row[0]:
            if row[0].upper() == col_upper:
                orig_type = row[1]
                orig_desc = row[2] if len(row) >= 3 else ""
                new_type = col_type if col_type is not None else orig_type
                new_desc = col_desc if col_desc is not None else orig_desc
                new_lines.append(f"| {row[0]} | {new_type} | {new_desc} |")
                modified = True
                continue
        new_lines.append(line)

    if not modified:
        raise GovernanceError(f"[DBG201] Column '{col_name}' not found in '{doc_path}'.", exit_code=1)

    out_text = "\n".join(new_lines) + "\n"
    if write:
        doc_path.write_text(out_text, encoding="utf-8")
    return out_text, write


def remove_column_from_doc(
    doc_path: Path,
    col_name: str,
    write: bool = False,
    yes: bool = False,
) -> tuple[str, bool]:
    """Removes a column row from the markdown table in doc_path."""
    if not doc_path.exists():
        raise GovernanceError(f"[DBG003] Target document file '{doc_path}' does not exist.", exit_code=2)

    if write and not yes:
        raise GovernanceError(
            f"[DBG003] Removing column '{col_name}' requires explicit confirmation '--write --yes'.",
            exit_code=2,
        )

    lines = doc_path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    col_upper = col_name.upper()
    removed = False

    for line in lines:
        row = _parse_table_row(line)
        if row and len(row) >= 2 and "---" not in row[0]:
            if row[0].upper() == col_upper:
                removed = True
                continue
        new_lines.append(line)

    if not removed:
        raise GovernanceError(f"[DBG201] Column '{col_name}' not found in '{doc_path}'.", exit_code=1)

    out_text = "\n".join(new_lines) + "\n"
    if write and yes:
        doc_path.write_text(out_text, encoding="utf-8")
    return out_text, write

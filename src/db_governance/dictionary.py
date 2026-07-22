"""Dictionary governance and naming standard validation module."""

from pathlib import Path
import tomllib
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from db_governance.errors import ProfileError
from db_governance.models import Finding, Severity
from db_governance.render import TableSpec


class DictionaryProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    name: str = "standard-dictionary"
    terms: dict[str, str] = Field(default_factory=dict)
    domains: dict[str, str] = Field(default_factory=dict)


def load_dictionary(dictionary_path: Path) -> DictionaryProfile:
    """Loads and validates data dictionary profile TOML.

    Args:
        dictionary_path: Resolved path to dictionary TOML file.

    Returns:
        Validated DictionaryProfile instance.

    Raises:
        ProfileError: If file is missing (DBG001) or invalid (DBG002).
    """
    resolved_path = dictionary_path.resolve()
    if not resolved_path.exists() or not resolved_path.is_file():
        raise ProfileError(f"[DBG001] Dictionary file not found: {resolved_path}", exit_code=2)

    try:
        content = resolved_path.read_bytes()
        data: dict[str, Any] = tomllib.loads(content.decode("utf-8"))
        profile = DictionaryProfile.model_validate(data)
        return profile
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"[DBG002] Invalid TOML in dictionary {resolved_path}: {exc}", exit_code=2) from exc
    except ValidationError as exc:
        raise ProfileError(f"[DBG002] Validation failed for dictionary {resolved_path}:\n{exc}", exit_code=2) from exc


def validate_dictionary_standards(
    tables: list[TableSpec], dict_prof: DictionaryProfile
) -> list[Finding]:
    """Validates table specifications against dictionary terms and domain data types.

    Returns:
        List of findings (DBG501 for non-standard terms or domain mismatch).
    """
    findings: list[Finding] = []

    for table in tables:
        for col in table.columns:
            col_upper = col.name.upper()

            # 1. Term check
            if col_upper in dict_prof.terms:
                recommended = dict_prof.terms[col_upper]
                findings.append(
                    Finding(
                        code="DBG501",
                        severity=Severity.ERROR,
                        message=f"Table {table.name} column '{col.name}' is non-standard. Recommended term is '{recommended}'.",
                        paths=[],
                    )
                )

            # 2. Domain type check
            for domain_suffix, std_type in dict_prof.domains.items():
                dom_upper = domain_suffix.upper()
                if col_upper.endswith(dom_upper) or col_upper.endswith("_" + dom_upper):
                    actual_type = col.data_type.upper()
                    expected_type = std_type.upper()
                    if actual_type != expected_type and not actual_type.startswith(expected_type):
                        findings.append(
                            Finding(
                                code="DBG501",
                                severity=Severity.WARNING,
                                message=f"Table {table.name} column '{col.name}' type '{col.data_type}' does not match standard domain '{domain_suffix}' type '{std_type}'.",
                                paths=[],
                            )
                        )

    return findings

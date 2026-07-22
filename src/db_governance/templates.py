"""Candidate profile template generation and rendering."""

from pathlib import Path
import tomllib
from typing import Any
from pydantic import ValidationError

from db_governance.errors import ProfileError
from db_governance.models import ProjectProfile

GENERIC_TEMPLATE_TOML = """version = 1
name = "{project_name}"

[[artifact_groups]]
name = "table-docs"
role = "source"
patterns = ["database/tables/**/*.md"]
required = true

[[artifact_groups]]
name = "migrations"
role = "migration"
patterns = ["database/migrations/*.sql"]
required = true

[[artifact_groups]]
name = "changelog"
role = "history"
patterns = ["database/CHANGELOG.md"]
required = true

[[rules]]
id = "DBDOC-001"
description = "A semantic table document change requires a migration and changelog update."
when_changed_any = ["database/tables/**/*.md"]
applies_to = ["semantic", "unknown"]
severity = "error"

[[rules.require_changed]]
label = "migration"
match_any = ["database/migrations/*.sql"]

[[rules.require_changed]]
label = "changelog update"
match_any = ["database/CHANGELOG.md"]
"""


def render_candidate_profile(
    project_root: Path, template_path: Path | None = None
) -> str:
    """Renders candidate TOML profile without writing to disk.

    Args:
        project_root: Path to project root.
        template_path: Optional path to external template TOML file.

    Returns:
        TOML formatted string representing candidate project profile.

    Raises:
        ProfileError: If external template is invalid or missing.
    """
    if template_path is not None:
        resolved_template = template_path.resolve()
        if not resolved_template.exists() or not resolved_template.is_file():
            raise ProfileError(
                f"[DBG001] Specified template file not found: {resolved_template}", exit_code=2
            )

        content = resolved_template.read_text(encoding="utf-8")
        try:
            data: dict[str, Any] = tomllib.loads(content)
            profile = ProjectProfile.model_validate(data)
        except (tomllib.TOMLDecodeError, ValidationError) as exc:
            raise ProfileError(
                f"[DBG002] Specified template {resolved_template} is invalid:\n{exc}", exit_code=2
            ) from exc

        if profile.version != 1:
            raise ProfileError(
                f"[DBG002] Specified template {resolved_template} has unsupported version {profile.version}.",
                exit_code=2,
            )

        return content

    proj_name = project_root.resolve().name
    return GENERIC_TEMPLATE_TOML.format(project_name=proj_name)

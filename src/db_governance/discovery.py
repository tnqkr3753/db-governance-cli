"""Artifact discovery using profile glob patterns."""

from pathlib import Path
from db_governance.errors import GovernanceError
from db_governance.models import ProjectProfile


def discover_artifacts(
    project_root: Path, profile: ProjectProfile
) -> dict[str, list[str]]:
    """Discovers matching files for each artifact group in the profile.

    Args:
        project_root: Path to project root.
        profile: Validated ProjectProfile instance.

    Returns:
        Dictionary mapping artifact group name to sorted list of project-relative POSIX paths.

    Raises:
        GovernanceError: If patterns escape project root or symlinks escape root (DBG003).
    """
    resolved_root = project_root.resolve()
    result: dict[str, list[str]] = {}

    for group in profile.artifact_groups:
        matched_set: set[str] = set()
        for pattern in group.patterns:
            if pattern.startswith("..") or "/../" in pattern or pattern.endswith("/.."):
                raise GovernanceError(
                    f"[DBG003] Pattern '{pattern}' attempts to escape project root.", exit_code=2
                )

            try:
                matches = list(resolved_root.glob(pattern))
            except Exception as exc:
                raise GovernanceError(
                    f"[DBG003] Invalid glob pattern '{pattern}' in group '{group.name}': {exc}",
                    exit_code=2,
                ) from exc

            for file_path in matches:
                if not file_path.is_file():
                    continue

                resolved_file = file_path.resolve()
                if not resolved_file.is_relative_to(resolved_root):
                    raise GovernanceError(
                        f"[DBG003] Matched file '{file_path}' resolves outside project root: {resolved_file}",
                        exit_code=2,
                    )

                rel_path = file_path.relative_to(resolved_root).as_posix()
                matched_set.add(rel_path)

        result[group.name] = sorted(matched_set)

    return result

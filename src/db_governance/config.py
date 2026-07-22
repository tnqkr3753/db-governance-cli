"""Profile loading and configuration parsing."""

import hashlib
from pathlib import Path
import tomllib
from typing import Any
from pydantic import ValidationError

from db_governance.errors import ProfileError
from db_governance.models import ProjectProfile


def load_profile(
    project_root: Path, profile_path: Path | None = None
) -> tuple[Path, ProjectProfile, str]:
    """Loads and validates a database governance profile TOML file.

    Args:
        project_root: Resolved path to project root.
        profile_path: Optional explicit path to profile file.

    Returns:
        Tuple of (resolved profile path, ProjectProfile instance, SHA-256 profile hash).

    Raises:
        ProfileError: If profile file is missing (DBG001), malformed, or invalid (DBG002).
    """
    resolved_root = project_root.resolve()
    if profile_path is not None:
        target_path = profile_path.resolve()
    else:
        target_path = (resolved_root / ".db-governance.toml").resolve()

    if not target_path.exists() or not target_path.is_file():
        raise ProfileError(f"[DBG001] Profile file not found: {target_path}", exit_code=2)

    try:
        content_bytes = target_path.read_bytes()
    except Exception as exc:
        raise ProfileError(f"[DBG001] Could not read profile file {target_path}: {exc}", exit_code=2) from exc

    profile_hash = hashlib.sha256(content_bytes).hexdigest()

    try:
        data: dict[str, Any] = tomllib.loads(content_bytes.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"[DBG002] Invalid TOML syntax in profile {target_path}: {exc}", exit_code=2) from exc

    try:
        profile = ProjectProfile.model_validate(data)
    except ValidationError as exc:
        raise ProfileError(f"[DBG002] Profile validation failed for {target_path}:\n{exc}", exit_code=2) from exc

    if profile.version != 1:
        raise ProfileError(
            f"[DBG002] Unsupported profile version {profile.version} in {target_path}. Expected version 1.",
            exit_code=2,
        )

    return target_path, profile, profile_hash

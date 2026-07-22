"""DDL migration version series manager module."""

import datetime
import re
from pathlib import Path

from db_governance.errors import GovernanceError
from db_governance.models import ArtifactRole, ProjectProfile


def get_next_migration_version(
    project_root: Path,
    profile: ProjectProfile,
    series_name: str = "main",
) -> tuple[str, Path]:
    """Computes next migration version string (e.g. 'V1_26') and target directory path."""
    resolved_root = project_root.resolve()

    target_series = next((s for s in profile.version_series if s.name.lower() == series_name.lower()), None)
    if target_series:
        mig_dir = (resolved_root / target_series.directory).resolve()
    else:
        mig_dir = resolved_root / "database" / "migrations"
        for group in profile.artifact_groups:
            if group.role == ArtifactRole.MIGRATION and group.patterns:
                pat = group.patterns[0]
                pat_dir = Path(pat.split("*")[0]).parent if "*" in pat else Path(pat).parent
                mig_dir = (resolved_root / pat_dir).resolve()
                break

    mig_files: list[Path] = list(mig_dir.glob("*.sql")) if mig_dir.exists() else []

    if not mig_files and mig_dir.exists():
        mig_files = list(mig_dir.glob("*.sql"))

    max_major = 1
    max_minor = 0

    version_pattern = re.compile(r"^V(\d+)(?:_(\d+))?__", re.IGNORECASE)

    for f in mig_files:
        m = version_pattern.match(f.name)
        if m:
            major = int(m.group(1))
            minor = int(m.group(2)) if m.group(2) is not None else 0
            if (major, minor) > (max_major, max_minor):
                max_major, max_minor = major, minor

    if max_minor > 0 or any("_" in f.name.split("__")[0] for f in mig_files):
        next_minor = max_minor + 1
        next_ver_str = f"V{max_major}_{next_minor:02d}"
    else:
        next_major = max_major + 1 if mig_files else 1
        next_ver_str = f"V{next_major}"

    mig_dir.mkdir(parents=True, exist_ok=True)
    return next_ver_str, mig_dir


def create_migration_file(
    project_root: Path,
    profile: ProjectProfile,
    slug: str,
    series_name: str = "main",
) -> Path:
    """Safely creates a new migration DDL template file with next computed version."""
    next_ver, mig_dir = get_next_migration_version(project_root, profile, series_name)
    clean_slug = slug.strip().lower().replace("-", "_").replace(" ", "_")
    target_path = mig_dir / f"{next_ver}__{clean_slug}.sql"

    if target_path.exists():
        raise GovernanceError(f"[DBG401] Migration file '{target_path}' already exists.", exit_code=2)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = [
        f"-- Migration: {target_path.name}",
        f"-- Created: {now_str}",
        f"-- Description: Migration script for {clean_slug}",
        "",
        "-- TODO: Add DDL SQL statements below",
        "",
    ]
    target_path.write_text("\n".join(header), encoding="utf-8")
    return target_path

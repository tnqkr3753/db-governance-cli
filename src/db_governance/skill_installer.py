"""Agent skill installer module for database-governance and database-migration-design skills."""

import os
from pathlib import Path
import shutil

from db_governance.errors import GovernanceError


def get_agent_skill_directory(agent_name: str, project_root: Path | None = None) -> Path:
    """Resolves target skill directory for given agent type or project path."""
    home = Path.home()
    if project_root is not None:
        return (project_root.resolve() / ".skills").resolve()

    name = agent_name.lower()
    if name == "gemini":
        return home / ".gemini" / "config" / "skills"
    elif name == "codex":
        return home / ".agents" / "skills"
    elif name == "claude":
        return home / ".claude" / "skills"
    else:
        raise GovernanceError(f"[DBG002] Unknown agent type '{agent_name}'. Supported: gemini, codex, claude, all.", exit_code=2)


def get_skill_source_directories() -> list[tuple[str, Path]]:
    """Locates package skill source directories."""
    base_package = Path(__file__).parent / "skills"
    skills = []
    for s_dir in ("database-governance", "database-migration-design"):
        src = base_package / s_dir
        if not src.exists():
            # Fallback to local workspace root
            src = Path(__file__).parent.parent.parent / "skills" / s_dir
        skills.append((s_dir, src.resolve()))
    return skills


def install_skill_to_agent(
    agent_name: str,
    project_root: Path | None = None,
    overwrite: bool = False,
    symlink: bool = False,
) -> Path:
    """Installs or symlinks package skills to the specified agent environment or project."""
    target_dir = get_agent_skill_directory(agent_name, project_root=project_root)
    target_dir.mkdir(parents=True, exist_ok=True)

    for skill_name, src_dir in get_skill_source_directories():
        if not src_dir.exists():
            raise GovernanceError(f"[DBG001] Skill source directory not found for '{skill_name}': {src_dir}", exit_code=2)

        dest_dir = target_dir / skill_name

        if dest_dir.exists() or dest_dir.is_symlink():
            if not overwrite:
                raise GovernanceError(
                    f"[DBG401] Target skill directory '{dest_dir}' already exists. Use --overwrite to replace.",
                    exit_code=2,
                )
            if dest_dir.is_symlink() or dest_dir.is_file():
                dest_dir.unlink()
            else:
                shutil.rmtree(dest_dir)

        if symlink:
            os.symlink(src_dir, dest_dir)
        else:
            shutil.copytree(src_dir, dest_dir)

    return target_dir

import re
from db_governance.models import (
    ChangeType,
    Finding,
    ProjectProfile,
    Severity,
)

def _match_path(pattern: str, path_str: str) -> bool:
    """Checks if a relative path matches a glob pattern (supporting **)."""
    norm_pattern = pattern.lstrip("./").lstrip("/")
    norm_path = path_str.lstrip("./").lstrip("/")

    # Step 1: Escape regex special chars except * and ?
    # We replace ** first with placeholders
    p = norm_pattern.replace("/**/", "/__DOUBLESTAR_SLASH__/")
    p = p.replace("**/", "__DOUBLESTAR_SLASH__/")
    p = p.replace("**", "__DOUBLESTAR__")

    # Escape remaining chars
    escaped = re.escape(p)

    # Convert placeholders to regex
    escaped = escaped.replace(r"/__DOUBLESTAR_SLASH__/", r"/(?:.*/)?")
    escaped = escaped.replace(r"__DOUBLESTAR_SLASH__/", r"(?:.*/)?")
    escaped = escaped.replace(r"__DOUBLESTAR__", r".*")

    # Convert single wildcard * and ?
    escaped = escaped.replace(r"\*", r"[^/]*")
    escaped = escaped.replace(r"\?", r"[^/]")

    regex = "^" + escaped + "$"
    return re.match(regex, norm_path) is not None


def evaluate_required_artifacts(
    profile: ProjectProfile, artifacts: dict[str, list[str]]
) -> list[Finding]:
    """Evaluates artifact inventory against required artifact group declarations.

    Returns:
        List of findings (DBG101 for required artifact groups with zero files).
    """
    findings: list[Finding] = []
    for group in profile.artifact_groups:
        if group.required and len(artifacts.get(group.name, [])) == 0:
            findings.append(
                Finding(
                    code="DBG101",
                    severity=Severity.ERROR,
                    message=f"Required artifact group '{group.name}' has no matching files in project.",
                    paths=[],
                    rule_id=None,
                )
            )
    return findings


def evaluate_rules(
    profile: ProjectProfile, changed_files: list[str], change_type: ChangeType
) -> list[Finding]:
    """Evaluates profile synchronization rules against changed files.

    Args:
        profile: Validated ProjectProfile instance.
        changed_files: List of relative POSIX path strings of changed files.
        change_type: SEMANTIC, FORMATTING, or UNKNOWN.

    Returns:
        List of findings (DBG201 for unsynchronized changes, DBG202 for unknown change type).
    """
    if change_type == ChangeType.FORMATTING:
        # Formatting changes bypass semantic sync rules
        return []

    findings: list[Finding] = []

    if change_type == ChangeType.UNKNOWN:
        findings.append(
            Finding(
                code="DBG202",
                severity=Severity.WARNING,
                message="Change type is 'unknown'; conservative semantic synchronization rules applied.",
                paths=changed_files,
                rule_id=None,
            )
        )

    for rule in profile.rules:
        # Check if rule applies to this change_type
        if change_type not in rule.applies_to and ChangeType.UNKNOWN not in rule.applies_to:
            continue

        # Check if any changed file matches any when_changed_any pattern
        matching_trigger_files: list[str] = []
        for changed_path in changed_files:
            for pattern in rule.when_changed_any:
                if _match_path(pattern, changed_path):
                    matching_trigger_files.append(changed_path)
                    break

        if not matching_trigger_files:
            continue

        # Rule triggered: check each requirement
        for req in rule.require_changed:
            requirement_satisfied = False
            for changed_path in changed_files:
                for req_pattern in req.match_any:
                    if _match_path(req_pattern, changed_path):
                        requirement_satisfied = True
                        break
                if requirement_satisfied:
                    break

            if not requirement_satisfied:
                findings.append(
                    Finding(
                        code="DBG201",
                        severity=rule.severity,
                        message=f"Rule {rule.id}: change requires updating {req.label}.",
                        paths=matching_trigger_files,
                        rule_id=rule.id,
                    )
                )

    return findings

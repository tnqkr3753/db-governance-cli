"""Execution engine for explicit project validators."""

import os
from pathlib import Path
import subprocess
import time

from db_governance.errors import GovernanceError
from db_governance.models import Finding, Severity, ValidatorResult, ValidatorSpec


def _mask_secrets(text: str) -> str:
    """Masks environment variable secrets appearing in command output."""
    if not text:
        return text

    masked = text
    for key, val in os.environ.items():
        if not val or len(val) < 3:
            continue
        key_upper = key.upper()
        if (
            key_upper.endswith("_PASSWORD")
            or key_upper.endswith("_SECRET")
            or key_upper.endswith("_TOKEN")
            or key_upper.endswith("_KEY")
        ):
            masked = masked.replace(val, "***REDACTED***")
    return masked


def run_validators(
    project_root: Path, specs: list[ValidatorSpec]
) -> tuple[list[ValidatorResult], list[Finding]]:
    """Runs configured project validators securely with shell=False.

    Args:
        project_root: Resolved path to project root.
        specs: List of ValidatorSpec configurations.

    Returns:
        Tuple of (list of ValidatorResult, list of Findings for validator failures).

    Raises:
        GovernanceError: If validator cwd escapes project root (DBG003).
    """
    resolved_root = project_root.resolve()
    results: list[ValidatorResult] = []
    findings: list[Finding] = []

    for spec in specs:
        spec_cwd = (resolved_root / spec.cwd).resolve()
        if not spec_cwd.is_relative_to(resolved_root):
            raise GovernanceError(
                f"[DBG003] Validator working directory '{spec.cwd}' escapes project root.",
                exit_code=2,
            )

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                spec.argv,
                cwd=spec_cwd,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
                shell=False,
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            stdout = _mask_secrets(proc.stdout[: spec.max_output_bytes])
            stderr = _mask_secrets(proc.stderr[: spec.max_output_bytes])

            results.append(
                ValidatorResult(
                    name=spec.name,
                    argv=spec.argv,
                    exit_code=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    duration_ms=duration_ms,
                )
            )

            if proc.returncode != 0:
                findings.append(
                    Finding(
                        code="DBG301",
                        severity=Severity.ERROR,
                        message=f"Project validator '{spec.name}' failed with exit code {proc.returncode}.",
                        paths=[],
                    )
                )

        except subprocess.TimeoutExpired:
            duration_ms = spec.timeout_seconds * 1000
            results.append(
                ValidatorResult(
                    name=spec.name,
                    argv=spec.argv,
                    exit_code=124,
                    stdout="",
                    stderr=f"Timed out after {spec.timeout_seconds} seconds",
                    duration_ms=duration_ms,
                )
            )
            findings.append(
                Finding(
                    code="DBG302",
                    severity=Severity.ERROR,
                    message=f"Project validator '{spec.name}' timed out after {spec.timeout_seconds} seconds.",
                    paths=[],
                )
            )
        except Exception as exc:
            results.append(
                ValidatorResult(
                    name=spec.name,
                    argv=spec.argv,
                    exit_code=127,
                    stdout="",
                    stderr=str(exc),
                    duration_ms=0,
                )
            )
            findings.append(
                Finding(
                    code="DBG302",
                    severity=Severity.ERROR,
                    message=f"Project validator '{spec.name}' could not be executed: {exc}",
                    paths=[],
                )
            )

    return results, findings

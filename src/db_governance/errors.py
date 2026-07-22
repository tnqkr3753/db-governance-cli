"""Custom exception classes and exit codes for db-governance."""


class GovernanceError(Exception):
    """Base exception for all db-governance errors.

    Attributes:
        message: Detailed error message.
        exit_code: Exit code for CLI process (0: success, 1: findings, 2: execution/usage error).
    """

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class ProfileError(GovernanceError):
    """Raised when profile loading or validation fails."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message, exit_code=exit_code)

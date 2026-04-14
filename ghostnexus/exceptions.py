"""GhostNexus SDK exceptions."""


class GhostNexusError(Exception):
    """Base exception for the GhostNexus SDK."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(GhostNexusError):
    """Invalid or expired API key."""


class InsufficientCreditsError(GhostNexusError):
    """Not enough credits to run the job."""


class JobFailedError(GhostNexusError):
    """The job failed on the provider side."""
    def __init__(self, message: str, job_id: str = None, logs: str = None):
        super().__init__(message)
        self.job_id = job_id
        self.logs = logs


class TimeoutError(GhostNexusError):
    """The job did not complete within the timeout."""


class ValidationError(GhostNexusError):
    """The script was rejected by the security policy."""

"""GhostNexus SDK data models."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserInfo:
    """Information about the authenticated user."""
    email: str
    credit_balance: float
    api_key_prefix: str
    is_admin: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "UserInfo":
        return cls(
            email=data["email"],
            credit_balance=float(data["credit_balance"]),
            api_key_prefix=data["api_key_prefix"],
            is_admin=data.get("is_admin", False),
        )


@dataclass
class JobResult:
    """Result of a completed job."""
    job_id: str
    status: str          # success | failed
    output: Optional[str] = None
    duration_seconds: Optional[float] = None
    cost_credits: Optional[float] = None
    task_name: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == "success"

    @classmethod
    def from_dict(cls, data: dict) -> "JobResult":
        return cls(
            job_id=data["job_id"],
            status=data["status"],
            output=data.get("output_logs"),
            duration_seconds=data.get("duration_seconds"),
            cost_credits=float(data["cost_credits"]) if data.get("cost_credits") else None,
            task_name=data.get("task_name"),
        )


@dataclass
class Job:
    """
    Represents a job submitted to the GhostNexus network.
    Call .wait() to block until completion, or poll manually with client.status().
    """
    job_id: str
    task_name: str
    status: str = "pending"
    _client: object = field(default=None, repr=False)

    def wait(self, timeout: int = 600, poll_interval: int = 3) -> JobResult:
        """
        Wait for the job to complete (blocking).

        Args:
            timeout: Maximum wait time in seconds (default 600s = 10 min).
            poll_interval: Polling interval in seconds.

        Returns:
            JobResult with status, output, cost.

        Raises:
            TimeoutError: If job does not complete within timeout.
            JobFailedError: If the job failed.
        """
        import time
        from .exceptions import TimeoutError, JobFailedError

        start = time.time()
        while True:
            result = self._client.status(self.job_id)
            if result.status in ("success", "failed"):
                if result.status == "failed":
                    raise JobFailedError(
                        f"Job {self.job_id} failed",
                        job_id=self.job_id,
                        logs=result.output,
                    )
                return result
            if time.time() - start > timeout:
                raise TimeoutError(
                    f"Job {self.job_id} not completed after {timeout}s"
                )
            time.sleep(poll_interval)

    @classmethod
    def from_dict(cls, data: dict, client=None) -> "Job":
        return cls(
            job_id=data["job_id"],
            task_name=data.get("task_name", ""),
            status=data.get("status", "pending"),
            _client=client,
        )

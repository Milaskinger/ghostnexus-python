"""
GhostNexus Python SDK — Client
"""
import os
import pathlib
from typing import List, Optional

import requests

from .exceptions import (
    AuthenticationError,
    GhostNexusError,
    InsufficientCreditsError,
    ValidationError,
)
from .models import Job, JobResult, UserInfo

_DEFAULT_BASE_URL = "https://ghostnexus.net"


class Client:
    """
    GhostNexus API client.

    Args:
        api_key: Your GhostNexus API key (starts with gn_live_).
                 If not provided, reads the GHOSTNEXUS_API_KEY environment variable.
        base_url: API base URL (default: https://ghostnexus.net)
        timeout:  HTTP timeout in seconds (default: 30)

    Example:
        >>> import ghostnexus
        >>> client = ghostnexus.Client(api_key="gn_live_...")
        >>> job = client.run("train.py")
        >>> result = job.wait()
        >>> print(result.output)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = 30,
    ):
        self._api_key = api_key or os.environ.get("GHOSTNEXUS_API_KEY", "")
        if not self._api_key:
            raise AuthenticationError(
                "Missing API key. Pass api_key= or set the GHOSTNEXUS_API_KEY "
                "environment variable.\n"
                "Get your key at https://ghostnexus.net/dashboard"
            )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"x-api-key": self._api_key})

    # ── Account ───────────────────────────────────────────────────────────────

    def me(self) -> UserInfo:
        """Return account information (email, credits)."""
        data = self._get("/api/me")
        return UserInfo.from_dict(data)

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def run(
        self,
        script: str,
        task_name: Optional[str] = None,
        inline: bool = False,
    ) -> Job:
        """
        Submit a Python script to the GhostNexus GPU network.

        Args:
            script:    Path to a .py file OR inline Python code if inline=True.
            task_name: Job name (shown in dashboard). Defaults to the filename.
            inline:    If True, `script` is treated as Python source code directly.

        Returns:
            Job — call .wait() to block until completion.

        Raises:
            AuthenticationError: Invalid API key.
            InsufficientCreditsError: Not enough credits.
            ValidationError: Script rejected by security policy.
            GhostNexusError: Other API error.

        Example:
            >>> job = client.run("train.py")
            >>> result = job.wait()

            >>> job = client.run("import torch; print(torch.__version__)", inline=True)
            >>> result = job.wait(timeout=60)
        """
        if inline:
            script_content = script
            name = task_name or "inline_script"
        else:
            path = pathlib.Path(script)
            if not path.exists():
                raise FileNotFoundError(f"Script not found: {script}")
            script_content = path.read_text(encoding="utf-8")
            name = task_name or path.name

        data = self._post("/api/jobs", {
            "script_content": script_content,
            "task_name": name,
        })
        return Job.from_dict(data, client=self)

    def status(self, job_id: str) -> JobResult:
        """
        Return the current status of a job.

        Args:
            job_id: Job identifier returned by .run().

        Returns:
            JobResult with status (pending/dispatched/success/failed), output, cost.
        """
        data = self._get(f"/api/jobs/{job_id}")
        return JobResult.from_dict(data)

    def history(self, limit: int = 50, offset: int = 0) -> List[JobResult]:
        """
        Return job history (paginated).

        Args:
            limit:  Number of results (max 500).
            offset: Pagination offset.
        """
        data = self._get("/api/jobs/history", params={"limit": limit, "offset": offset})
        return [JobResult.from_dict(j) for j in data]

    # ── Credits ───────────────────────────────────────────────────────────────

    def balance(self) -> float:
        """Return available credit balance in USD."""
        return self.me().credit_balance

    # ── Internal HTTP ─────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict = None) -> dict:
        resp = self._session.get(
            f"{self._base_url}{path}",
            params=params,
            timeout=self._timeout,
        )
        return self._handle(resp)

    def _post(self, path: str, payload: dict) -> dict:
        resp = self._session.post(
            f"{self._base_url}{path}",
            json=payload,
            timeout=self._timeout,
        )
        return self._handle(resp)

    @staticmethod
    def _handle(resp: requests.Response) -> dict:
        if resp.status_code == 401:
            raise AuthenticationError("Invalid or expired API key.", status_code=401)
        if resp.status_code == 402:
            detail = resp.json().get("detail", "Insufficient credits.")
            raise InsufficientCreditsError(detail, status_code=402)
        if resp.status_code == 422:
            errors = resp.json().get("detail", [])
            raise ValidationError(f"Script rejected: {errors}", status_code=422)
        if not resp.ok:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise GhostNexusError(detail, status_code=resp.status_code)
        return resp.json()

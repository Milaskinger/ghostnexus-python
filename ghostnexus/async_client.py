"""
GhostNexus Python SDK — Async Client (requires httpx)

Install with:  pip install ghostnexus[async]
"""
from __future__ import annotations

import os
import pathlib
from typing import AsyncGenerator, List, Optional

from .exceptions import (
    AuthenticationError,
    GhostNexusError,
    InsufficientCreditsError,
    ValidationError,
)
from .models import Job, JobResult, UserInfo

_DEFAULT_BASE_URL = "https://ghostnexus.net"


class AsyncClient:
    """
    Async GhostNexus client — drop-in replacement for Client, fully async.

    Requires httpx:  pip install ghostnexus[async]

    Example:
        import asyncio
        import ghostnexus

        async def main():
            async with ghostnexus.AsyncClient(api_key="gn_live_...") as client:
                job = await client.run("import torch; print(torch.__version__)", inline=True)
                async for chunk in job.stream_logs():
                    print(chunk, end="", flush=True)

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = 30,
    ):
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "AsyncClient requires httpx. Install with: pip install ghostnexus[async]"
            ) from None

        self._api_key = api_key or os.environ.get("GHOSTNEXUS_API_KEY", "")
        if not self._api_key:
            raise AuthenticationError(
                "Missing API key. Pass api_key= or set the GHOSTNEXUS_API_KEY "
                "environment variable.\n"
                "Get your key at https://ghostnexus.net/dashboard"
            )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None
        self._httpx = httpx

    async def __aenter__(self) -> "AsyncClient":
        self._http = self._httpx.AsyncClient(
            headers={"x-api-key": self._api_key},
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._http:
            await self._http.aclose()

    def _client(self) -> "httpx.AsyncClient":
        if self._http is None:
            self._http = self._httpx.AsyncClient(
                headers={"x-api-key": self._api_key},
                timeout=self._timeout,
            )
        return self._http

    # ── Account ───────────────────────────────────────────────────────────────

    async def me(self) -> UserInfo:
        """Return account information (email, credits)."""
        data = await self._get("/api/me")
        return UserInfo.from_dict(data)

    async def balance(self) -> float:
        """Return available credit balance in USD."""
        return (await self.me()).credit_balance

    # ── Jobs ──────────────────────────────────────────────────────────────────

    async def run(
        self,
        script: str,
        task_name: Optional[str] = None,
        inline: bool = False,
    ) -> "AsyncJob":
        """
        Submit a Python script to the GhostNexus GPU network.

        Args:
            script:    Path to a .py file OR inline Python code if inline=True.
            task_name: Job name shown in dashboard.
            inline:    If True, `script` is treated as Python source code directly.

        Returns:
            AsyncJob — call await job.wait() or async for chunk in job.stream_logs().

        Example:
            job = await client.run("train.py")
            result = await job.wait()

            job = await client.run("import torch; print(torch.__version__)", inline=True)
            async for chunk in job.stream_logs():
                print(chunk, end="")
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

        data = await self._post("/api/jobs", {
            "script_content": script_content,
            "task_name": name,
        })
        job = Job.from_dict(data, client=None)
        return AsyncJob(job_id=job.job_id, task_name=job.task_name, _async_client=self)

    async def status(self, job_id: str) -> JobResult:
        """Return the current status of a job."""
        data = await self._get(f"/api/jobs/{job_id}")
        return JobResult.from_dict(data)

    async def history(self, limit: int = 50, offset: int = 0) -> List[JobResult]:
        """Return job history (paginated)."""
        data = await self._get("/api/jobs/history", params={"limit": limit, "offset": offset})
        return [JobResult.from_dict(j) for j in data]

    # ── Internal HTTP ─────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict = None) -> dict:
        resp = await self._client().get(
            f"{self._base_url}{path}",
            params=params,
        )
        return self._handle(resp)

    async def _post(self, path: str, payload: dict) -> dict:
        resp = await self._client().post(
            f"{self._base_url}{path}",
            json=payload,
        )
        return self._handle(resp)

    @staticmethod
    def _handle(resp) -> dict:
        if resp.status_code == 401:
            raise AuthenticationError("Invalid or expired API key.", status_code=401)
        if resp.status_code == 402:
            detail = resp.json().get("detail", "Insufficient credits.")
            raise InsufficientCreditsError(detail, status_code=402)
        if resp.status_code == 422:
            errors = resp.json().get("detail", [])
            raise ValidationError(f"Script rejected: {errors}", status_code=422)
        if not resp.is_success:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise GhostNexusError(detail, status_code=resp.status_code)
        return resp.json()

    async def close(self) -> None:
        """Explicitly close the underlying HTTP session."""
        if self._http:
            await self._http.aclose()
            self._http = None


class AsyncJob:
    """Async handle for a submitted job."""

    def __init__(self, job_id: str, task_name: str, _async_client: AsyncClient):
        self.job_id = job_id
        self.task_name = task_name
        self.status = "pending"
        self._client = _async_client

    def __repr__(self) -> str:
        return f"AsyncJob(job_id={self.job_id!r}, status={self.status!r})"

    async def wait(self, timeout: int = 600, poll_interval: float = 3.0) -> JobResult:
        """
        Wait for the job to complete (non-blocking via asyncio.sleep).

        Raises:
            TimeoutError: If job does not complete within timeout.
            JobFailedError: If the job failed.
        """
        import asyncio
        from .exceptions import TimeoutError, JobFailedError
        import time

        start = time.monotonic()
        while True:
            result = await self._client.status(self.job_id)
            self.status = result.status
            if result.status in ("success", "failed"):
                if result.status == "failed":
                    raise JobFailedError(
                        f"Job {self.job_id} failed",
                        job_id=self.job_id,
                        logs=result.output,
                    )
                return result
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"Job {self.job_id} not completed after {timeout}s")
            await asyncio.sleep(poll_interval)

    async def stream_logs(
        self,
        timeout: int = 600,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator — yield log lines in real-time as the job runs.

        Example:
            async for chunk in job.stream_logs():
                print(chunk, end="", flush=True)
        """
        import asyncio
        from .exceptions import TimeoutError, JobFailedError
        import time

        start = time.monotonic()
        last_pos = 0

        while True:
            result = await self._client.status(self.job_id)

            if result.output and len(result.output) > last_pos:
                new_content = result.output[last_pos:]
                last_pos = len(result.output)
                yield new_content

            if result.status == "failed":
                raise JobFailedError(
                    f"Job {self.job_id} failed",
                    job_id=self.job_id,
                    logs=result.output,
                )
            if result.status == "success":
                return

            if time.monotonic() - start > timeout:
                raise TimeoutError(f"Job {self.job_id} not completed after {timeout}s")
            await asyncio.sleep(poll_interval)

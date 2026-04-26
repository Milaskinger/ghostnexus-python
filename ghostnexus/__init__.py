"""
GhostNexus Python SDK
~~~~~~~~~~~~~~~~~~~~~

Run Python scripts on the GhostNexus decentralized GPU network.
GDPR-compliant, EU-hosted, billed by the second.

Quick start:
    import ghostnexus
    client = ghostnexus.Client(api_key="gn_live_...")
    job = client.run("train.py")
    result = job.wait()
    print(result.output)

Full documentation: https://ghostnexus.net/docs
"""

from .client import Client
from .models import Job, JobResult, UserInfo
from .exceptions import (
    GhostNexusError,
    AuthenticationError,
    InsufficientCreditsError,
    JobFailedError,
    ValidationError,
    TimeoutError as GNTimeoutError,
)

__version__ = "0.2.0"
__all__ = [
    "Client",
    "AsyncClient",
    "Job",
    "JobResult",
    "UserInfo",
    "GhostNexusError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "JobFailedError",
    "ValidationError",
    "GNTimeoutError",
]


def __getattr__(name: str):
    if name == "AsyncClient":
        from .async_client import AsyncClient
        return AsyncClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

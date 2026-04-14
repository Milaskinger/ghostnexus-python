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
    TimeoutError as GNTimeoutError,
)

__version__ = "0.1.0"
__all__ = [
    "Client",
    "Job",
    "JobResult",
    "UserInfo",
    "GhostNexusError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "JobFailedError",
    "GNTimeoutError",
]

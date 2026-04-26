# ghostnexus — Python SDK

[![PyPI version](https://img.shields.io/pypi/v/ghostnexus.svg)](https://pypi.org/project/ghostnexus/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GDPR Compliant](https://img.shields.io/badge/GDPR-Compliant-blue.svg)](https://ghostnexus.net)
[![EU Hosted](https://img.shields.io/badge/Hosted-EU%20🇪🇺-blue.svg)](https://ghostnexus.net)

**Run Python scripts on RTX 4090 / A100 / H100 GPUs in 30 seconds. Pay per second. 40% cheaper than AWS.**

```python
import ghostnexus

client = ghostnexus.Client(api_key="gn_live_...")
job = client.run("train.py")
result = job.wait()
print(result.output)
```

---

## 💸 Price Comparison

| Provider        | GPU         | $/hour  | $/month (720h) |
|-----------------|-------------|---------|----------------|
| **GhostNexus**  | RTX 4090    | $0.50   | **$36**        |
| AWS             | A10G        | $1.01   | $727           |
| Google Cloud    | T4          | $0.35   | $252           |
| Lambda Labs     | A10         | $0.60   | $432           |
| RunPod          | RTX 4090    | $0.74   | $533           |

> GhostNexus is a decentralized GPU marketplace — compute comes from real GPU owners, not hyperscaler data centers.
> Servers are EU-hosted and GDPR-compliant. No lock-in. No subscription required.

---

## 🚀 Quick Start

### Install

```bash
# Sync client (zero extra deps)
pip install ghostnexus

# Async client (asyncio + httpx)
pip install ghostnexus[async]
```

### Get your API key

Sign up at [ghostnexus.net](https://ghostnexus.net) — you get **$15 free credits** with code `WELCOME15`.

### Run a script

```python
import ghostnexus

client = ghostnexus.Client(api_key="gn_live_YOUR_KEY")

# Run a file
job = client.run("train.py")
result = job.wait()
print(result.output)
print(f"Cost: ${result.cost_credits:.4f}")

# Run inline code
job = client.run(
    "import torch; print(torch.cuda.get_device_name(0))",
    inline=True,
)
result = job.wait(timeout=120)
print(result.output)  # NVIDIA GeForce RTX 4090
```

### Environment variable (recommended)

```bash
export GHOSTNEXUS_API_KEY="gn_live_YOUR_KEY"
```

```python
client = ghostnexus.Client()  # picks up key from env
```

---

## ⚡ Async Client (new in v0.2.0)

Full async/await support — drop-in replacement for `Client`.

```python
import asyncio
import ghostnexus

async def main():
    async with ghostnexus.AsyncClient() as client:
        job = await client.run("train.py")
        result = await job.wait(timeout=300)
        print(result.output)

asyncio.run(main())
```

### Stream logs in real time

```python
async def train_with_logs():
    async with ghostnexus.AsyncClient() as client:
        job = await client.run("train.py", task_name="resnet-train")

        async for chunk in job.stream_logs():
            print(chunk, end="", flush=True)

asyncio.run(train_with_logs())
```

### Submit multiple jobs concurrently

```python
import asyncio
import ghostnexus

async def run_parallel():
    async with ghostnexus.AsyncClient() as client:
        jobs = await asyncio.gather(
            client.run("preprocess.py"),
            client.run("augment.py"),
            client.run("validate.py"),
        )
        results = await asyncio.gather(*[j.wait() for j in jobs])
        total_cost = sum(r.cost_credits for r in results if r.cost_credits)
        print(f"All done — total cost: ${total_cost:.4f}")

asyncio.run(run_parallel())
```

---

## 📖 API Reference

### `Client(api_key, base_url, timeout)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `$GHOSTNEXUS_API_KEY` | Your API key |
| `base_url` | `str` | `https://ghostnexus.net` | API base URL |
| `timeout` | `int` | `30` | HTTP timeout (seconds) |

### Methods

#### `client.run(script, task_name=None, inline=False) → Job`

Submit a Python script to the GPU network.

```python
job = client.run("finetune.py", task_name="llama-finetune")
job = client.run("import torch; print(torch.__version__)", inline=True)
```

#### `job.wait(timeout=600, poll_interval=3) → JobResult`

Block until the job completes.

```python
result = job.wait(timeout=300)
print(result.output)           # stdout from your script
print(result.status)           # "success" or "failed"
print(result.duration_seconds)
print(result.cost_credits)
```

#### `job.stream_logs(timeout=600, poll_interval=1.0) → Generator[str]`

Stream stdout in real time (sync generator).

```python
for chunk in job.stream_logs():
    print(chunk, end="", flush=True)
```

#### `client.status(job_id) → JobResult`

```python
result = client.status("job-uuid-here")
if result.status == "success":
    print(result.output)
```

#### `client.history(limit=50, offset=0) → List[JobResult]`

```python
jobs = client.history(limit=10)
for job in jobs:
    print(f"{job.task_name}: {job.status} (${job.cost_credits:.4f})")
```

#### `client.balance() → float`

```python
print(f"Credits remaining: ${client.balance():.2f}")
```

#### `client.me() → UserInfo`

```python
info = client.me()
print(info.email, info.credit_balance)
```

### `AsyncClient` — same API, fully async

`AsyncClient` mirrors `Client` exactly but every method is `async`. Use as a context manager (`async with`) or call `await client.close()` when done.

| Sync | Async |
|------|-------|
| `client.run(...)` | `await client.run(...)` |
| `job.wait(...)` | `await job.wait(...)` |
| `for chunk in job.stream_logs()` | `async for chunk in job.stream_logs()` |
| `client.history()` | `await client.history()` |
| `client.balance()` | `await client.balance()` |

---

## 🖥️ CLI

The `ghostnexus` command is installed automatically.

```bash
# Configure (one-time)
ghostnexus configure

# Run the GPU benchmark demo
ghostnexus run --demo

# Run a script and wait for result
ghostnexus run train.py --wait

# Stream output in real time
ghostnexus run train.py --stream

# Run inline code
ghostnexus run --script "import torch; print(torch.__version__)" --wait

# Check job status
ghostnexus status <job_id>

# List recent jobs
ghostnexus history
ghostnexus history --limit 50

# Show credit balance
ghostnexus balance
```

---

## 🔥 Examples

### Fine-tune LLaMA 3 (QLoRA)

```python
import ghostnexus

client = ghostnexus.Client()
job = client.run("qlora_finetune.py", task_name="llama3-qlora")

for chunk in job.stream_logs(timeout=3600):
    print(chunk, end="", flush=True)
```

### Check GPU info

```python
import ghostnexus

client = ghostnexus.Client()
job = client.run("""
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print(f"CUDA: {torch.version.cuda}")
""", inline=True)

result = job.wait(timeout=60)
print(result.output)
```

### Batch pipeline

```python
client = ghostnexus.Client()
for script in ["preprocess.py", "train.py", "evaluate.py"]:
    job = client.run(script)
    result = job.wait()
    print(f"{result.task_name}: {result.duration_seconds:.1f}s — ${result.cost_credits:.4f}")
```

---

## ❌ Error Handling

```python
import ghostnexus
from ghostnexus import (
    AuthenticationError,
    InsufficientCreditsError,
    JobFailedError,
    ValidationError,
    GNTimeoutError,
)

try:
    job = client.run("train.py")
    result = job.wait()
except AuthenticationError:
    print("Invalid API key — get one at ghostnexus.net/dashboard")
except InsufficientCreditsError:
    print("Not enough credits — add credits at ghostnexus.net/dashboard")
except ValidationError as e:
    print(f"Script rejected by security policy: {e}")
except JobFailedError as e:
    print(f"Job failed:\n{e.logs}")
except GNTimeoutError:
    print("Job timed out")
```

---

## 🔧 Jupyter Integration

```
pip install ghostnexus
%load_ext ghostnexus_magic
%ghostnexus_config --api-key gn_live_YOUR_KEY

%%ghostnexus --task train-resnet --timeout 60
import torch
model = torch.hub.load('pytorch/vision', 'resnet50', pretrained=True).cuda()
print(f"GPU: {torch.cuda.get_device_name(0)}")
```

Full docs: [ghostnexus.net/integrations](https://ghostnexus.net/integrations)

---

## ⚙️ GitHub Actions Integration

```yaml
- name: Run GPU job on GhostNexus
  uses: Milaskinger/ghostnexus-run@v1
  with:
    api-key: ${{ secrets.GHOSTNEXUS_API_KEY }}
    script: train.py
    timeout-minutes: 30
```

---

## 🛡️ Security & Privacy

- API keys transmitted over HTTPS only
- Scripts run in isolated Docker containers with RestrictedPython AST validation
- GDPR-compliant — all data stays in the EU (Frankfurt)
- **Fully open source** — audit the code yourself

---

## 🤝 Contributing

```bash
git clone https://github.com/Milaskinger/ghostnexus-python
cd ghostnexus-python
pip install -e ".[dev]"
pytest
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🔗 Links

- [ghostnexus.net](https://ghostnexus.net) — Platform
- [Dashboard](https://ghostnexus.net/dashboard) — Manage jobs & credits
- [Integrations](https://ghostnexus.net/integrations) — GitHub Actions, Jupyter
- [PyPI](https://pypi.org/project/ghostnexus/) — Package
- [ghostnexus-node](https://github.com/Milaskinger/ghostnexus-node) — Provider node (share your GPU)
- [contact@ghostnexus.net](mailto:contact@ghostnexus.net) — Support

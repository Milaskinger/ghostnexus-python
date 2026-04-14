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
pip install ghostnexus
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
print(f"Cost: ${result.cost_credits:.4f} credits")

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
# From a file
job = client.run("finetune.py", task_name="llama-finetune")

# Inline
job = client.run("import torch; print(torch.__version__)", inline=True)
```

#### `job.wait(timeout=600, poll_interval=3) → JobResult`

Block until the job completes.

```python
result = job.wait(timeout=300)
print(result.output)          # stdout from your script
print(result.status)          # "success" or "failed"
print(result.duration_seconds)
print(result.cost_credits)
```

#### `client.status(job_id) → JobResult`

Poll a job without blocking.

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
print(info.email)
print(info.credit_balance)
```

---

## 🔥 Examples

### Train a model

```python
import ghostnexus

client = ghostnexus.Client()
job = client.run("train_resnet.py", task_name="resnet50-cifar10")
result = job.wait(timeout=3600)
print(result.output)
print(f"Trained in {result.duration_seconds:.0f}s for ${result.cost_credits:.4f}")
```

### Check GPU info (quick test)

```python
import ghostnexus

client = ghostnexus.Client()
job = client.run("""
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.version.cuda}")
""", inline=True)

result = job.wait(timeout=60)
print(result.output)
```

### Batch pipeline

```python
import ghostnexus

client = ghostnexus.Client()
for script in ["preprocess.py", "train.py", "evaluate.py"]:
    job = client.run(script)
    result = job.wait()
    print(f"✓ {result.task_name} — {result.duration_seconds:.1f}s")
```

---

## ❌ Error Handling

```python
import ghostnexus
from ghostnexus import AuthenticationError, InsufficientCreditsError, JobFailedError

try:
    job = client.run("train.py")
    result = job.wait()
except AuthenticationError:
    print("Invalid API key — get one at ghostnexus.net/dashboard")
except InsufficientCreditsError:
    print("Not enough credits — add credits at ghostnexus.net/dashboard")
except JobFailedError as e:
    print(f"Job failed: {e.logs}")
except ghostnexus.GNTimeoutError:
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
- Scripts run in isolated containers (RestrictedPython sandbox)
- GDPR-compliant — all data stays in the EU
- **Fully open source** — audit the code yourself

---

## 🤝 Contributing

Contributions are welcome!

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
- [contact@ghostnexus.net](mailto:contact@ghostnexus.net) — Support

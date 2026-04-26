"""
GhostNexus CLI — ghostnexus run / ghostnexus status / ghostnexus balance
"""
import argparse
import os
import sys
import time

DEMO_SCRIPT = """
import torch
import time

print("GhostNexus GPU Benchmark")
print("=" * 40)
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
print(f"CUDA: {torch.version.cuda if torch.cuda.is_available() else 'N/A'}")
print(f"PyTorch: {torch.__version__}")
device = "cuda" if torch.cuda.is_available() else "cpu"
results = []
for n in [1024, 2048, 4096]:
    a = torch.randn(n, n, device=device)
    b = torch.randn(n, n, device=device)
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    c = torch.matmul(a, b)
    if device == "cuda":
        torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    gflops = (2 * n ** 3) / dt / 1e9
    results.append((n, gflops, dt * 1000))
    print(f"  {n}x{n}  →  {gflops:.1f} GFLOP/s  ({dt*1000:.1f} ms)")
print("=" * 40)
print(f"Peak: {max(r[1] for r in results):.1f} GFLOP/s")
print("Benchmark complete.")
""".strip()


def _get_client():
    """Build a Client, exiting cleanly if credentials are missing."""
    try:
        from ghostnexus.client import Client
        return Client()
    except ImportError:
        print("ERROR: ghostnexus package not installed correctly.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Set GHOSTNEXUS_API_KEY or run: ghostnexus configure", file=sys.stderr)
        sys.exit(1)


def cmd_run(args):
    """ghostnexus run [--demo] [file.py] [--wait] [--task NAME]"""
    client = _get_client()

    if args.demo:
        print("Submitting GPU benchmark demo...")
        script_content = DEMO_SCRIPT
        task_name = args.task or "gpu-benchmark-demo"
        inline = True
    elif args.script:
        script_content = args.script
        task_name = args.task or "script"
        inline = True
    elif args.file:
        import pathlib
        path = pathlib.Path(args.file)
        if not path.exists():
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        script_content = path.read_text(encoding="utf-8")
        task_name = args.task or path.name
        inline = True
    else:
        print("ERROR: Provide a file, --demo, or --script 'code'", file=sys.stderr)
        sys.exit(1)

    try:
        job = client.run(script_content, task_name=task_name, inline=True)
        print(f"Job submitted: {job.job_id}")
        print(f"Task: {task_name}")
        print(f"Status: {job.status}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.stream:
        print("Streaming output (Ctrl-C to detach):")
        try:
            for chunk in job.stream_logs(timeout=300, poll_interval=1.0):
                print(chunk, end="", flush=True)
            result = client.status(job.job_id)
            print(f"\n{'='*40}")
            print(f"Status: {result.status}")
            if result.cost_credits is not None:
                print(f"Cost: ${result.cost_credits:.4f}")
        except KeyboardInterrupt:
            print(f"\nDetached. Poll: ghostnexus status {job.job_id}")
        except Exception as exc:
            print(f"\nERROR: {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.wait or args.demo:
        print("Waiting for result", end="", flush=True)
        try:
            result = job.wait(timeout=300, poll_interval=3)
            print(f"\n{'='*40}")
            if result.output:
                print(result.output)
            print(f"{'='*40}")
            print(f"Status: {result.status}")
            if result.cost_credits is not None:
                print(f"Cost: ${result.cost_credits:.4f}")
        except Exception as exc:
            print(f"\nERROR waiting for result: {exc}", file=sys.stderr)
            print(f"Check status: ghostnexus status {job.job_id}")
            sys.exit(1)
    else:
        print(f"\nPoll: ghostnexus status {job.job_id}")


def cmd_status(args):
    """ghostnexus status <job_id>"""
    client = _get_client()
    try:
        result = client.status(args.job_id)
        print(f"Job: {args.job_id}")
        print(f"Status: {result.status}")
        if result.task_name:
            print(f"Task: {result.task_name}")
        if result.duration_seconds is not None:
            print(f"Duration: {result.duration_seconds:.1f}s")
        if result.cost_credits is not None:
            print(f"Cost: ${result.cost_credits:.4f}")
        if result.output:
            print(f"\nOutput:\n{result.output}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_history(args):
    """ghostnexus history [--limit N]"""
    client = _get_client()
    try:
        jobs = client.history(limit=args.limit)
        if not jobs:
            print("No jobs found.")
            return
        print(f"{'Job ID':<36}  {'Status':<12}  {'Task':<24}  {'Cost':>8}  {'Duration':>10}")
        print("-" * 100)
        for j in jobs:
            cost = f"${j.cost_credits:.4f}" if j.cost_credits is not None else "—"
            dur = f"{j.duration_seconds:.1f}s" if j.duration_seconds is not None else "—"
            task = (j.task_name or "")[:24]
            print(f"{j.job_id:<36}  {j.status:<12}  {task:<24}  {cost:>8}  {dur:>10}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_balance(args):
    """ghostnexus balance"""
    client = _get_client()
    try:
        bal = client.balance()
        print(f"Credit balance: ${bal:.2f}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_configure(args):
    """ghostnexus configure — store API key"""
    key = input("Enter your GhostNexus API key (from dashboard > Settings): ").strip()
    if not key.startswith("gn_"):
        print("WARNING: Key doesn't look right (expected gn_live_...)", file=sys.stderr)

    config_dir = os.path.expanduser("~/.ghostnexus")
    os.makedirs(config_dir, mode=0o700, exist_ok=True)
    config_file = os.path.join(config_dir, "config")
    with open(config_file, "w") as f:
        f.write(f"GHOSTNEXUS_API_KEY={key}\n")
    os.chmod(config_file, 0o600)
    print(f"API key saved to {config_file}")
    print("You can now run: ghostnexus run --demo")


def main():
    parser = argparse.ArgumentParser(
        prog="ghostnexus",
        description="GhostNexus CLI — submit Python scripts to EU GPU nodes",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # run
    p_run = sub.add_parser("run", help="Submit a job to the GPU network")
    p_run.add_argument("file", nargs="?", help="Python script file to run")
    p_run.add_argument("--demo", action="store_true", help="Run the GPU benchmark demo")
    p_run.add_argument("--script", metavar="CODE", help="Inline Python code to run")
    p_run.add_argument("--task", metavar="NAME", help="Job name (shown in dashboard)")
    p_run.add_argument("--wait", action="store_true", help="Wait for result")
    p_run.add_argument("--stream", action="store_true", help="Stream output in real-time")
    p_run.set_defaults(func=cmd_run)

    # status
    p_status = sub.add_parser("status", help="Check job status")
    p_status.add_argument("job_id", help="Job ID to check")
    p_status.set_defaults(func=cmd_status)

    # balance
    p_bal = sub.add_parser("balance", help="Show credit balance")
    p_bal.set_defaults(func=cmd_balance)

    # history
    p_hist = sub.add_parser("history", help="List recent jobs")
    p_hist.add_argument("--limit", type=int, default=20, metavar="N", help="Number of jobs (default: 20)")
    p_hist.set_defaults(func=cmd_history)

    # configure
    p_cfg = sub.add_parser("configure", help="Save API key locally")
    p_cfg.set_defaults(func=cmd_configure)

    args = parser.parse_args()

    # Load config file if env var not set
    if not os.environ.get("GHOSTNEXUS_API_KEY"):
        config_file = os.path.expanduser("~/.ghostnexus/config")
        if os.path.exists(config_file):
            with open(config_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GHOSTNEXUS_API_KEY="):
                        os.environ["GHOSTNEXUS_API_KEY"] = line.split("=", 1)[1]
                        break

    args.func(args)


if __name__ == "__main__":
    main()

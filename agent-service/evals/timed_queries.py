#!/usr/bin/env python3
"""
Run timed test queries against the agent. Use for performance verification.
Usage: python evals/timed_queries.py [--url http://localhost:8000]
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

QUERIES = [
    "check interactions between ibuprofen and aspirin",
    "symptoms of chest pain and shortness of breath",
    "find a cardiologist in New York",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Agent base URL")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    print("Performance check: single-tool queries (target < 5s each)\n")
    print(f"Agent URL: {base}\n")

    with httpx.Client(timeout=60.0) as client:
        # 1. Health check
        try:
            t0 = time.perf_counter()
            r = client.get(f"{base}/health")
            elapsed = time.perf_counter() - t0
            r.raise_for_status()
            print(f"[1] GET /health: {elapsed*1000:.0f} ms — OK")
        except Exception as e:
            print(f"[1] GET /health: FAILED — {e}")
            return 1

        # 2. Timed chat queries
        for i, query in enumerate(QUERIES, start=2):
            try:
                t0 = time.perf_counter()
                resp = client.post(f"{base}/chat", json={"message": query})
                elapsed = time.perf_counter() - t0
                resp.raise_for_status()
                data = resp.json()
                text = (data.get("response") or "")[:120]
                tools_used = data.get("tools_used") or []
                under_5 = "✓" if elapsed < 5.0 else "✗ (over 5s)"
                print(f"[{i}] \"{query[:50]}...\"")
                print(f"    Time: {elapsed:.2f} s {under_5}")
                print(f"    Tools: {[t.get('name') for t in tools_used]}")
                print(f"    Response: {text!r}...")
                print()
            except httpx.HTTPStatusError as e:
                body = (e.response.text or "")[:300]
                print(f"[{i}] \"{query[:50]}...\" — HTTP {e.response.status_code}: {body}\n")
                return 1
            except Exception as e:
                print(f"[{i}] \"{query[:50]}...\" — FAILED: {e}\n")
                return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

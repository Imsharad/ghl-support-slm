"""Measure the actual /support HTTP route on development prompts, serially.

This measures client-observed warm latency and sustained serial throughput, not
maximum concurrent capacity or time to first token. Raw requests and failures are
retained. The first request is an uncontrolled-cache warmup, not a cold benchmark.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from serve.bench import hardware_info, percentile
from train.repro import sha256_file


def request_json(url: str, payload: dict | None = None, timeout: float = 120) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def verify_response(response: dict, model: str, health: dict) -> None:
    if (response.get("model") != model or response.get("model_digest") != health["models"][model]["digest"]
            or response.get("prompt_sha256") != health["prompt_sha256"]):
        raise ValueError("response model/prompt identity differs from benchmark start")
    if not isinstance(response.get("answer"), str) or not response["answer"].strip():
        raise ValueError("empty or absent answer")
    for field in ("prompt_tokens", "gen_tokens"):
        if type(response.get(field)) is not int or response[field] < 1:
            raise ValueError(f"invalid {field}")
    for field in ("latency_ms", "request_latency_ms", "tokens_per_s"):
        value = response.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid {field}")
    if type(response.get("truncated")) is not bool:
        raise ValueError("missing truncation status")


def timed_request(url: str, model: str, row: dict, health: dict, *, call=request_json) -> dict:
    start = time.perf_counter()
    response = None
    try:
        response = call(url.rstrip("/") + "/support", {"model": model, "query": row["instruction"]})
        verify_response(response, model, health)
        error = None
    except Exception as exc:
        # Preserve failures, but do not dump arbitrary backend error bodies or credentials.
        error = {"type": type(exc).__name__, "message": str(exc) if isinstance(exc, ValueError) else "HTTP request failed"}
        if isinstance(exc, urllib.error.HTTPError):
            error["http_status"] = exc.code
    return {"id": row["id"], "client_latency_ms": (time.perf_counter() - start) * 1000,
            "response": response, "error": error}


def summarize(rows: list[dict], wall_seconds: float) -> dict:
    if not rows or not math.isfinite(wall_seconds) or wall_seconds <= 0:
        raise ValueError("nonempty measurements and positive wall time required")
    success = [row for row in rows if row["error"] is None]
    latencies = [row["client_latency_ms"] for row in success]
    tokens = sum(row["response"]["gen_tokens"] for row in success)
    return {"attempts": len(rows), "successes": len(success), "failures": len(rows) - len(success),
            "p50_success_client_latency_ms": percentile(latencies, .5) if latencies else None,
            "p95_success_client_latency_ms": percentile(latencies, .95) if latencies else None,
            "measured_wall_seconds": wall_seconds,
            "successful_requests_per_wall_second": len(success) / wall_seconds,
            "successful_generated_tokens_per_wall_second": tokens / wall_seconds,
            "total_successful_generated_tokens": tokens,
            "truncated_successes": sum(row["response"]["truncated"] for row in success),
            "latency_scope": "Successful HTTP requests; failures reported separately and included in elapsed throughput denominator."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8013")
    parser.add_argument("--dev", type=Path, default=ROOT / "data/processed/v3-candidate03/val.jsonl")
    parser.add_argument("--models", nargs="+", choices=("base", "tuned"), default=["base", "tuned"])
    parser.add_argument("--requests", type=int, default=54)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--hardware-note", required=True, help="Explicit server placement/hardware observation; do not guess")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("use a new output directory; measurements are append-only")
    if args.requests < 1 or args.warmup < 1 or len(set(args.models)) != len(args.models):
        parser.error("positive counts and unique model aliases required")
    rows = [json.loads(line) for line in args.dev.read_text().splitlines() if line.strip()]
    if (len(rows) < args.requests or len({row["id"] for row in rows}) != len(rows)
            or any(not isinstance(row.get("instruction"), str) or not row["instruction"].strip() for row in rows)):
        raise ValueError("expected sufficient unique development rows with instruction text, not final challenge items")
    rows = rows[:args.requests]
    health = request_json(args.api_url.rstrip("/") + "/health")
    if any(model not in health.get("models", {}) for model in args.models):
        raise ValueError("requested model is not configured; no benchmark fallback")
    args.output_dir.mkdir(parents=True)
    metadata = {"schema": 1, "started_at": datetime.now(timezone.utc).isoformat(),
                "api_url": args.api_url, "health_at_start": health, "dev_sha256": sha256_file(args.dev),
                "benchmark_sha256": sha256_file(Path(__file__)), "client_hardware": hardware_info(),
                "server_hardware_note": args.hardware_note,
                "concurrency": 1, "warmup_requests_per_model": args.warmup, "requests_per_model": args.requests,
                "model_order": args.models, "prompt_order": [row["id"] for row in rows],
                "limitations": ["Serial warm requests, not saturation capacity or streaming TTFT.",
                                "Initial cache state uncontrolled; warmup is not a cold-start measurement.",
                                "Models run sequentially; time/thermal/background-load confounding is possible.",
                                "Client hardware is measured locally; the server placement note is operator-supplied.",
                                "Answers and token lengths differ; latency alone is not a quality comparison."]}
    with (args.output_dir / "metadata.json").open("x") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")
    summaries = {}
    for model in args.models:
        warmups, measured = [], []
        with (args.output_dir / f"{model}-requests.jsonl").open("x") as handle:
            for index in range(args.warmup):
                record = timed_request(args.api_url, model, rows[index % len(rows)], health)
                warmups.append(record)
                handle.write(json.dumps(dict(record, phase="warmup")) + "\n")
                handle.flush()
            if any(row["error"] for row in warmups):
                raise ValueError("warmup failed; partial evidence preserved, fix infrastructure before measuring")
            start = time.perf_counter()
            for row in rows:
                record = timed_request(args.api_url, model, row, health)
                measured.append(record)
                handle.write(json.dumps(dict(record, phase="measured")) + "\n")
                handle.flush()
                print(f"{model} {len(measured)}/{len(rows)} {'FAIL' if record['error'] else 'OK'}", flush=True)
            elapsed = time.perf_counter() - start
        summaries[model] = summarize(measured, elapsed)
    final_health = request_json(args.api_url.rstrip("/") + "/health")
    report = {"models": summaries, "health_at_end": final_health,
              "identities_unchanged": final_health == health,
              "pass": final_health == health and all(summary["failures"] == 0 for summary in summaries.values())}
    with (args.output_dir / "summary.json").open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

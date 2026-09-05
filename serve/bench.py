#!/usr/bin/env python3
"""Benchmark an Ollama model on a fixed serial slice of the development set."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    from serve.inference import DEFAULT_OLLAMA_URL, fixed_messages, post_json
except ModuleNotFoundError:  # Direct execution: python serve/bench.py
    from inference import DEFAULT_OLLAMA_URL, fixed_messages, post_json

ROOT = Path(__file__).resolve().parents[1]
DEV_PATH = ROOT / "eval" / "dev.jsonl"
RESULTS_PATH = ROOT / "serve" / "bench_results.json"
WARMUP_REQUESTS = 5
REQUIRED_REQUEST_FIELDS = (
    "id",
    "prompt_tokens",
    "generated_tokens",
    "end_to_end_ms",
    "generation_tokens_s",
    "error",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--model", choices=("ghl-base", "ghl-support"), default="ghl-base")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--dev", type=Path, default=DEV_PATH)
    parser.add_argument("--output", type=Path, default=RESULTS_PATH)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def load_prompts(path: Path, count: int) -> list[dict[str, str]]:
    if count < 1:
        raise ValueError("--requests must be at least 1")
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            item_id = value.get("id")
            query = value.get("query")
            if not isinstance(item_id, str) or not isinstance(query, str) or not query.strip():
                raise ValueError(f"{path}:{line_number} has invalid id/query")
            rows.append({"id": item_id, "query": query})
            if len(rows) == count:
                break
    if len(rows) != count:
        raise ValueError(f"{path} has {len(rows)} usable rows; need {count}")
    return rows


def native_chat(base_url: str, model: str, query: str, *, keep_alive: str = "5m") -> dict[str, Any]:
    return post_json(
        f"{base_url.rstrip('/')}/api/chat",
        {
            "model": model,
            "messages": fixed_messages(query),
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": 0,
                "top_p": 1.0,
                "repeat_penalty": 1.0,
                "num_predict": 256,
                "num_ctx": 2048,
                "seed": 42,
            },
        },
    )


def unload_model(base_url: str, model: str) -> None:
    result = post_json(
        f"{base_url.rstrip('/')}/api/generate",
        {"model": model, "prompt": "", "stream": False, "keep_alive": 0},
    )
    if result.get("done") is not True:
        raise RuntimeError(f"Ollama did not confirm unloading {model}")


def ns_to_ms(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return None
    return round(float(value) / 1_000_000, 3)


def timed_request(base_url: str, model: str, row: dict[str, str]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = native_chat(base_url, model, row["query"])
        elapsed_ms = (time.perf_counter() - started) * 1000
        message = response.get("message")
        answer = message.get("content") if isinstance(message, dict) else None
        prompt_tokens = response.get("prompt_eval_count")
        generated_tokens = response.get("eval_count")
        eval_duration = response.get("eval_duration")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("empty answer")
        if not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool):
            raise RuntimeError("missing prompt_eval_count")
        if not isinstance(generated_tokens, int) or isinstance(generated_tokens, bool):
            raise RuntimeError("missing eval_count")
        if not isinstance(eval_duration, int) or eval_duration <= 0:
            raise RuntimeError("missing eval_duration")
        return {
            "id": row["id"],
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,
            "end_to_end_ms": round(elapsed_ms, 3),
            "generation_tokens_s": round(generated_tokens / (eval_duration / 1e9), 3),
            "load_ms": ns_to_ms(response.get("load_duration")),
            "prompt_eval_ms": ns_to_ms(response.get("prompt_eval_duration")),
            "generation_ms": ns_to_ms(eval_duration),
            "error": None,
        }
    except Exception as exc:
        return {
            "id": row["id"],
            "prompt_tokens": None,
            "generated_tokens": None,
            "end_to_end_ms": round((time.perf_counter() - started) * 1000, 3),
            "generation_tokens_s": None,
            "load_ms": None,
            "prompt_eval_ms": None,
            "generation_ms": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile of an empty list")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def command_output(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (result.stdout or result.stderr).strip()
    return text or None


def hardware_info() -> dict[str, Any]:
    chip = command_output(["sysctl", "-n", "machdep.cpu.brand_string"])
    memory = command_output(["sysctl", "-n", "hw.memsize"])
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": chip or platform.processor() or "unknown",
        "logical_cpu_count": os.cpu_count(),
        "memory_bytes": int(memory) if memory and memory.isdigit() else None,
    }


def validate_block(block: dict[str, Any], expected_requests: int) -> list[str]:
    errors: list[str] = []
    requests = block.get("requests")
    if not isinstance(requests, list) or len(requests) != expected_requests:
        return [f"requests must contain exactly {expected_requests} rows"]
    for index, row in enumerate(requests):
        if not isinstance(row, dict):
            errors.append(f"requests[{index}] is not an object")
            continue
        missing = [field for field in REQUIRED_REQUEST_FIELDS if field not in row]
        if missing:
            errors.append(f"requests[{index}] missing {', '.join(missing)}")
        if row.get("error") is not None:
            errors.append(f"requests[{index}] failed: {row['error']}")
    summary = block.get("summary")
    required_summary = (
        "request_count",
        "failure_count",
        "p50_end_to_end_ms",
        "p95_end_to_end_ms",
        "mean_generation_tokens_s",
        "total_generated_tokens",
        "measured_wall_seconds",
        "total_tokens_per_wall_second",
        "cold_load_ms",
        "cold_first_request_ms",
    )
    if not isinstance(summary, dict):
        errors.append("summary is missing")
    else:
        for field in required_summary:
            if summary.get(field) is None:
                errors.append(f"summary.{field} is missing")
        if summary.get("request_count") != expected_requests:
            errors.append("summary.request_count does not match --requests")
        if summary.get("failure_count") != 0:
            errors.append("summary.failure_count is not zero")
    if block.get("warmup_requests") != WARMUP_REQUESTS:
        errors.append(f"warmup_requests must be {WARMUP_REQUESTS}")
    if not block.get("ollama_version"):
        errors.append("ollama_version is missing")
    if not isinstance(block.get("hardware"), dict):
        errors.append("hardware is missing")
    return errors


def write_results(path: Path, model: str, block: dict[str, Any]) -> None:
    existing: dict[str, Any] = {}
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"{path} is not a JSON object")
        existing = loaded
    existing[model] = block
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(existing, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    if args.concurrency != 1:
        raise ValueError("this reproducibility benchmark is serial; --concurrency must be 1")
    rows = load_prompts(args.dev, args.requests)

    unload_model(args.base_url, args.model)
    cold_started = time.perf_counter()
    cold_response = native_chat(args.base_url, args.model, rows[0]["query"])
    cold_first_request_ms = (time.perf_counter() - cold_started) * 1000
    cold_load_ms = ns_to_ms(cold_response.get("load_duration"))
    if cold_load_ms is None:
        raise RuntimeError("cold request did not report load_duration")

    for index in range(WARMUP_REQUESTS):
        warmup = native_chat(args.base_url, args.model, rows[index % len(rows)]["query"])
        message = warmup.get("message")
        if not isinstance(message, dict) or not str(message.get("content", "")).strip():
            raise RuntimeError(f"warmup {index + 1} returned an empty answer")

    measured_started = time.perf_counter()
    request_rows = [timed_request(args.base_url, args.model, row) for row in rows]
    measured_wall_seconds = time.perf_counter() - measured_started

    successful = [row for row in request_rows if row["error"] is None]
    failures = [row for row in request_rows if row["error"] is not None]
    latencies = [float(row["end_to_end_ms"]) for row in successful]
    rates = [float(row["generation_tokens_s"]) for row in successful]
    total_generated_tokens = sum(int(row["generated_tokens"]) for row in successful)
    summary = {
        "request_count": len(request_rows),
        "failure_count": len(failures),
        "p50_end_to_end_ms": round(percentile(latencies, 0.50), 3) if latencies else None,
        "p95_end_to_end_ms": round(percentile(latencies, 0.95), 3) if latencies else None,
        "mean_generation_tokens_s": round(statistics.fmean(rates), 3) if rates else None,
        "total_generated_tokens": total_generated_tokens,
        "measured_wall_seconds": round(measured_wall_seconds, 3),
        "total_tokens_per_wall_second": round(
            total_generated_tokens / measured_wall_seconds, 3
        ) if measured_wall_seconds > 0 else None,
        "cold_load_ms": cold_load_ms,
        "cold_first_request_ms": round(cold_first_request_ms, 3),
    }
    block = {
        "measured_at": datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
            "%Y-%m-%d %H:%M:%S IST"
        ),
        "model": args.model,
        "backend": "ollama",
        "dev_file": str(args.dev.resolve().relative_to(ROOT)),
        "warmup_requests": WARMUP_REQUESTS,
        "concurrency": args.concurrency,
        "decoding": {
            "temperature": 0,
            "top_p": 1.0,
            "repeat_penalty": 1.0,
            "max_new_tokens": 256,
            "num_ctx": 2048,
            "seed": 42,
        },
        "ollama_version": command_output(["ollama", "--version"]),
        "hardware": hardware_info(),
        "summary": summary,
        "requests": request_rows,
    }
    write_results(args.output, args.model, block)

    check_errors = validate_block(block, args.requests)
    print(json.dumps({"model": args.model, "summary": summary}, indent=2))
    if args.check and check_errors:
        for error in check_errors:
            print(f"CHECK FAILED: {error}", file=sys.stderr)
        return 1
    if args.check:
        print("CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

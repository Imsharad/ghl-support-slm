#!/usr/bin/env python3
"""Verify local prerequisites for training or serving the pinned model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSIONS_PATH = ROOT / "configs" / "versions.json"
PROMPT_PATH = ROOT / "configs" / "prompt.txt"
SOURCES_PATH = ROOT / "artifacts" / "sources.json"
OLLAMA_VERSION_URL = "http://localhost:11434/api/version"
EXPECTED_PROMPT = (
    "You are a customer support assistant. Answer clearly and helpfully. "
    "Do not invent company policy, account details, or completed actions. "
    "Ask for missing context when needed. Never ask for passwords or full "
    "payment card details."
)
GIB = 1024**3


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    details: str
    hard: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--training", action="store_true", help="check training prerequisites")
    mode.add_argument("--serve", action="store_true", help="check local serving prerequisites")
    return parser.parse_args()


def markdown_table(checks: list[Check]) -> str:
    lines = [
        "| Check | Status | Required | Details |",
        "|---|---|---|---|",
    ]
    for check in checks:
        details = check.details.replace("|", "\\|").replace("\n", " ")
        required = "yes" if check.hard else "no"
        lines.append(f"| {check.name} | {check.status} | {required} | {details} |")
    return "\n".join(lines)


def load_versions(checks: list[Check]) -> dict[str, object]:
    try:
        versions = json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))
        revision = versions["base_model"]["revision"]  # type: ignore[index]
        checks.append(Check("Version manifest", "PASS", f"base revision {revision}", True))
        return versions
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        checks.append(Check("Version manifest", "FAIL", str(exc), True))
        return {}


def hugging_face_cache() -> Path:
    if value := os.environ.get("HF_HUB_CACHE"):
        return Path(value).expanduser()
    if value := os.environ.get("HF_HOME"):
        return Path(value).expanduser() / "hub"
    if value := os.environ.get("XDG_CACHE_HOME"):
        return Path(value).expanduser() / "huggingface" / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def check_model_cache(checks: list[Check], versions: dict[str, object]) -> None:
    try:
        model = versions["base_model"]
        repo_id = model["repo_id"]  # type: ignore[index]
        revision = model["revision"]  # type: ignore[index]
        snapshot = (
            hugging_face_cache()
            / f"models--{str(repo_id).replace('/', '--')}"
            / "snapshots"
            / str(revision)
        )
        required = {
            "LICENSE",
            "config.json",
            "generation_config.json",
            "merges.txt",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.json",
        }
        missing = sorted(name for name in required if not (snapshot / name).is_file())
        if missing:
            checks.append(
                Check("Pinned model metadata", "FAIL", f"missing: {', '.join(missing)}", True)
            )
        else:
            checks.append(
                Check(
                    "Pinned model metadata",
                    "PASS",
                    f"7 files at {snapshot}",
                    True,
                )
            )
    except (KeyError, TypeError) as exc:
        checks.append(Check("Pinned model metadata", "FAIL", f"invalid manifest: {exc}", True))


def check_prompt(checks: list[Check]) -> None:
    try:
        raw = PROMPT_PATH.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        prompt = raw.decode("utf-8").strip()
        if prompt != EXPECTED_PROMPT:
            checks.append(
                Check("System prompt", "FAIL", f"content mismatch; sha256 {digest}", True)
            )
        else:
            checks.append(Check("System prompt", "PASS", f"sha256 {digest}", True))
    except (OSError, UnicodeDecodeError) as exc:
        checks.append(Check("System prompt", "FAIL", str(exc), True))


def check_sources(checks: list[Check]) -> None:
    try:
        source = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        if not isinstance(source, dict):
            raise TypeError("manifest root must be a JSON object")
        revision = source.get("revision", "revision key not found")
        checks.append(Check("Dataset source manifest", "PASS", f"revision {revision}", True))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        checks.append(Check("Dataset source manifest", "FAIL", str(exc), True))


def ollama_version(binary: str) -> str:
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"version check failed: {type(exc).__name__}"
    output = " ".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return output or f"exit {result.returncode}"


def check_ollama(checks: list[Check], *, serving: bool) -> None:
    binary = shutil.which("ollama")
    if binary:
        checks.append(Check("Ollama binary", "PASS", f"{binary}; {ollama_version(binary)}", serving))
    else:
        status = "FAIL" if serving else "WARN"
        checks.append(Check("Ollama binary", status, "not found on PATH", serving))

    try:
        with urllib.request.urlopen(OLLAMA_VERSION_URL, timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        checks.append(Check("Ollama API", "PASS", f"reachable; version {payload.get('version', 'unknown')}"))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        checks.append(
            Check(
                "Ollama API",
                "WARN",
                f"not reachable at {OLLAMA_VERSION_URL} ({type(exc).__name__}); server was not started",
            )
        )


def check_torch(checks: list[Check], *, training: bool) -> None:
    try:
        import torch

        if torch.cuda.is_available():
            device = f"cuda ({torch.cuda.get_device_name(0)})"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        checks.append(Check("Torch device", "PASS", f"torch {torch.__version__}; {device}", True))
        if training:
            if torch.cuda.is_available():
                checks.append(Check("QLoRA CUDA", "PASS", "CUDA is available"))
            else:
                checks.append(
                    Check(
                        "QLoRA CUDA",
                        "WARN",
                        "CUDA is unavailable; the primary QLoRA run belongs on Colab/Kaggle; "
                        "local MPS viability is tracked separately by DAG node D0",
                    )
                )
    except (ImportError, RuntimeError) as exc:
        checks.append(Check("Torch device", "FAIL", str(exc), True))


def collect_checks(*, training: bool) -> list[Check]:
    checks: list[Check] = []

    python_ok = sys.version_info[:2] == (3, 11)
    checks.append(
        Check(
            "Python",
            "PASS" if python_ok else "FAIL",
            f"{sys.version.split()[0]} (requires 3.11.x)",
            True,
        )
    )

    uv = shutil.which("uv")
    checks.append(Check("uv", "PASS" if uv else "FAIL", uv or "not found on PATH", True))

    free_gib = shutil.disk_usage(ROOT).free / GIB
    checks.append(
        Check(
            "Disk free",
            "PASS" if free_gib >= 30 else "FAIL",
            f"{free_gib:.1f} GiB (requires at least 30 GiB)",
            True,
        )
    )

    versions = load_versions(checks)
    check_ollama(checks, serving=not training)
    check_model_cache(checks, versions)
    check_prompt(checks)
    check_sources(checks)
    check_torch(checks, training=training)
    return checks


def save_report(checks: list[Check], *, mode: str) -> Path:
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    report_path = ROOT / "docs" / f"preflight-{now:%Y-%m-%d-%H%M}IST.md"
    hard_failures = [check.name for check in checks if check.hard and check.status == "FAIL"]
    warnings = [check.name for check in checks if check.status == "WARN"]
    verdict = "FAIL" if hard_failures else "PASS"
    body = "\n".join(
        [
            "# Preflight report",
            "",
            f"Generated: {now:%Y-%m-%d %H:%M:%S IST}",
            f"Mode: `{mode}`",
            f"Verdict: **{verdict}**",
            "",
            markdown_table(checks),
            "",
            f"Hard failures: {', '.join(hard_failures) if hard_failures else 'none'}.",
            f"Warnings: {', '.join(warnings) if warnings else 'none'}.",
            "",
        ]
    )
    report_path.write_text(body, encoding="utf-8")
    return report_path


def main() -> int:
    args = parse_args()
    mode = "training" if args.training else "serve"
    checks = collect_checks(training=args.training)
    table = markdown_table(checks)
    print(table)
    try:
        report_path = save_report(checks, mode=mode)
        print(f"\nReport: {report_path}")
    except OSError as exc:
        print(f"\nReport: FAIL ({exc})", file=sys.stderr)
        return 1

    hard_failures = [check for check in checks if check.hard and check.status == "FAIL"]
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

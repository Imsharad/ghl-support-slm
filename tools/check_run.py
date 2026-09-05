#!/usr/bin/env python3
"""Gate a training run directory before its adapter is trusted.

Checks, in order:
  1. loss.csv exists, has rows, and every train and validation loss is finite.
  2. At least one validation loss was recorded.
  3. config.json records peak_memory_gb and it is under the limit (12 GB default).
  4. The newest adapter checkpoint reloads onto the pinned base and generates one answer.
  5. If the run was a smoke run, smoke.json says the resume reproduced the losses.

Exits 0 when every check passes, 1 otherwise, with the failures listed.

Usage:
    uv run python tools/check_run.py train/runs/ghl-support-qlora
    uv run python tools/check_run.py train/runs/smoke-ghl-support-qlora --no-generate
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKPOINT_PREFIX = "checkpoint-"
SAMPLE_QUERY = "I forgot my password and cannot sign in. What should I do?"


def read_loss_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def newest_checkpoint(run_dir: Path) -> Path | None:
    found: list[tuple[int, Path]] = []
    for path in run_dir.glob(f"{CHECKPOINT_PREFIX}*"):
        if path.is_dir() and (path / "adapter_config.json").is_file():
            try:
                found.append((int(path.name.removeprefix(CHECKPOINT_PREFIX)), path))
            except ValueError:
                continue
    return sorted(found)[-1][1] if found else None


def check_losses(run_dir: Path, failures: list[str]) -> None:
    loss_csv = run_dir / "loss.csv"
    if not loss_csv.is_file():
        failures.append(f"missing {loss_csv}")
        return
    rows = read_loss_csv(loss_csv)
    if not rows:
        failures.append(f"{loss_csv} has no rows")
        return
    val_seen = 0
    for row in rows:
        for field in ("train_loss", "val_loss"):
            raw = (row.get(field) or "").strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError:
                failures.append(f"step {row.get('step')}: {field}={raw!r} is not a number")
                continue
            if not math.isfinite(value):
                failures.append(f"step {row.get('step')}: {field} is {value}")
            elif field == "val_loss":
                val_seen += 1
    if val_seen == 0:
        failures.append(f"{loss_csv} records no validation loss")
    print(f"loss.csv: {len(rows)} logged steps, {val_seen} with a validation loss")


def check_memory(run_dir: Path, limit_gb: float, failures: list[str]) -> dict[str, Any]:
    config_json = run_dir / "config.json"
    if not config_json.is_file():
        failures.append(f"missing {config_json}")
        return {}
    summary = json.loads(config_json.read_text(encoding="utf-8"))
    peak = summary.get("peak_memory_gb")
    if peak is None:
        failures.append("config.json has no peak_memory_gb (did the run finish?)")
    elif float(peak) >= limit_gb:
        failures.append(f"peak_memory_gb {peak} is not below the {limit_gb} GB limit")
    else:
        print(f"peak memory: {peak} GB (limit {limit_gb} GB)")
    if summary.get("git_sha"):
        print(f"git sha: {summary['git_sha']}")
    return summary


def check_smoke(run_dir: Path, failures: list[str]) -> None:
    smoke_json = run_dir / "smoke.json"
    if not smoke_json.is_file():
        return
    report = json.loads(smoke_json.read_text(encoding="utf-8"))
    if not report.get("ok"):
        failures.append(
            f"smoke.json says the resume did not reproduce the losses "
            f"(max_abs_diff={report.get('max_abs_diff')}, tolerance={report.get('tolerance')})"
        )
    else:
        print(
            f"smoke resume: matched at steps {report.get('compared_steps')}, "
            f"max_abs_diff {report.get('max_abs_diff')}"
        )


def check_generation(run_dir: Path, device: str, failures: list[str]) -> None:
    checkpoint = newest_checkpoint(run_dir)
    if checkpoint is None:
        failures.append(f"no {CHECKPOINT_PREFIX}* directory with an adapter_config.json in {run_dir}")
        return
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from train.render import load_base_pin, render_prompt
    except ImportError as exc:
        failures.append(f"cannot import the training stack for the reload check: {exc}")
        return

    repo_id, revision = load_base_pin()
    if device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    print(f"reloading {checkpoint.name} on {device}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(repo_id, revision=revision, local_files_only=True)
        base = AutoModelForCausalLM.from_pretrained(
            repo_id,
            revision=revision,
            local_files_only=True,
            dtype=torch.float16 if device != "cpu" else torch.float32,
        )
        model = PeftModel.from_pretrained(base, str(checkpoint))
        model.to(device)
        model.eval()
        prompt = render_prompt(SAMPLE_QUERY, tokenizer)
        encoded = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        inputs = {name: tensor.to(device) for name, tensor in encoded.items()}
        with torch.no_grad():
            output = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=64,
                pad_token_id=tokenizer.eos_token_id,
            )
        answer = tokenizer.decode(
            output[0, inputs["input_ids"].shape[-1] :], skip_special_tokens=True
        ).strip()
    except Exception as exc:
        failures.append(f"adapter reload or generation failed: {exc}")
        return
    if not answer:
        failures.append("the reloaded adapter generated an empty answer")
        return
    print("sample answer:")
    print(answer)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--max-memory-gb", type=float, default=12.0)
    parser.add_argument("--device", default="auto", choices=("auto", "cuda", "mps", "cpu"))
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="skip the adapter reload; use only when the weights are on another machine",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    if not run_dir.is_dir():
        print(f"FAIL: run directory not found: {run_dir}", file=sys.stderr)
        return 1

    print(f"checking {run_dir}")
    failures: list[str] = []
    check_losses(run_dir, failures)
    check_memory(run_dir, args.max_memory_gb, failures)
    check_smoke(run_dir, failures)
    if args.no_generate:
        print("generation check skipped (--no-generate)")
    else:
        check_generation(run_dir, args.device, failures)

    if failures:
        print(f"\nFAIL: {len(failures)} problem(s)", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1
    reload_note = "" if args.no_generate else " and the adapter reloads"
    print(f"\nPASS: run directory is complete{reload_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

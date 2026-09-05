#!/usr/bin/env python3
"""QLoRA supervised fine-tuning for Qwen2.5-1.5B-Instruct on the grouped Bitext split.

One optimizer step is ``grad_accum`` micro-batches of ``micro_batch_size`` rows.
Rows are encoded once through ``train.collate.AssistantOnlyCollator`` so the loss
mask is the same object the fixtures test. The run directory is self-describing:
``config.json`` carries the resolved config, the git sha, the installed versions
and the measured peak memory; ``loss.csv`` carries train and validation loss;
``checkpoint-<step>/`` carries the adapter plus enough state to resume.

Usage:
    uv run python train/train.py --config configs/train.yaml
    uv run python train/train.py --config configs/train.yaml --resume
    uv run python train/train.py --config configs/train.yaml --smoke
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import resource
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
# Running this file as a script puts train/ on sys.path, where train.py shadows the
# train package. Drop that entry so `train.collate` resolves to the package.
_HERE = str(Path(__file__).resolve().parent)
sys.path[:] = [entry for entry in sys.path if entry not in ("", _HERE)]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from train.collate import IGNORE_INDEX, AssistantOnlyCollator  # noqa: E402
from train.render import load_base_pin  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
VERSIONS_PATH = ROOT / "configs" / "versions.json"
CHECKPOINT_PREFIX = "checkpoint-"
LOSS_CSV_FIELDS = (
    "step",
    "epoch",
    "lr",
    "train_loss",
    "val_loss",
    "elapsed_s",
    "peak_memory_gb",
)


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def log(message: str) -> None:
    print(f"[{now_ist()}] {message}", flush=True)


# --------------------------------------------------------------------------- config


def load_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def apply_smoke(config: dict[str, Any]) -> dict[str, Any]:
    """Shrink a config to the 20-step smoke shape described in docs/TRAINING.md."""
    smoke = dict(config.get("smoke") or {})
    config = json.loads(json.dumps(config))  # deep copy through plain JSON types
    config["run_name"] = smoke.get("run_name", f"smoke-{config['run_name']}")
    config["data"]["dir"] = smoke.get("data_dir", config["data"]["dir"])
    config["data"]["cap_train"] = smoke.get("rows", 64)
    config["train"]["grad_accum"] = smoke.get("grad_accum", 1)
    config["train"]["max_steps"] = smoke.get("steps", 20)
    config["train"]["log_every"] = smoke.get("log_every", 5)
    config["train"]["save_every"] = smoke.get("save_every", 10)
    config["train"]["val_batches"] = smoke.get("val_batches", 4)
    config["train"]["checkpoint_fractions"] = []
    config["hub"]["push_checkpoints"] = False
    return config


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


# --------------------------------------------------------------------------- device


def select_device(requested: str, torch: Any) -> str:
    if requested not in {"auto", "cuda", "mps", "cpu"}:
        raise SystemExit(f"unknown device {requested!r}; use auto, cuda, mps or cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "device 'cuda' was requested but no CUDA GPU is visible.\n"
            "This config targets Colab Pro (A100 or L4) or a free T4.\n"
            "On the M1 Pro Mac run the same config with --device mps: node D0 measured\n"
            "2.567 s/step for this exact shape (docs/LOCAL_QLORA_PROBE.md), about 1.5 h\n"
            "for a 2,000-step epoch. Use --device cpu only for a correctness check."
        )
    if requested == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("device 'mps' was requested but Metal is not available on this machine")
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def peak_memory_gb(device: str, torch: Any) -> float:
    if device == "cuda":
        return torch.cuda.max_memory_allocated() / 1e9
    if device == "mps" and hasattr(torch.mps, "driver_allocated_memory"):
        return torch.mps.driver_allocated_memory() / 1e9
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes, Linux reports kibibytes.
    return usage / 1e9 if sys.platform == "darwin" else usage * 1024 / 1e9


# --------------------------------------------------------------------------- data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(
            f"data file not found: {path}\n"
            "Regenerate the split with: uv run python data/prepare.py"
        )
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{number} is not valid JSON: {exc}") from exc
    if not rows:
        raise SystemExit(f"{path} has no rows")
    return rows


def cap_rows(rows: list[dict[str, Any]], cap: int | None, seed: int) -> list[dict[str, Any]]:
    """Cap the train split with the same group-aware routine data/prepare.py uses."""
    if cap is None or len(rows) <= cap:
        return rows
    if all("group_id" in row for row in rows):
        from data.prepare import cap_train_rows

        return cap_train_rows(rows, cap, seed=seed)
    return rows[:cap]


def encode_rows(
    rows: Sequence[dict[str, Any]],
    collator: AssistantOnlyCollator,
    *,
    label: str,
) -> list[dict[str, list[int]]]:
    encoded: list[dict[str, list[int]]] = []
    dropped = 0
    for index, row in enumerate(rows, start=1):
        item = collator.encode(row)
        if item is None:
            dropped += 1
            continue
        encoded.append(item)
        if index % 2000 == 0:
            log(f"encoding {label}: {index}/{len(rows)}")
    if not encoded:
        raise SystemExit(f"every {label} row was dropped at max_length {collator.max_length}")
    if dropped:
        log(f"{label}: dropped {dropped} rows over {collator.max_length} tokens")
    return encoded


def pad_batch(items: Sequence[dict[str, list[int]]], pad_id: int, torch: Any) -> dict[str, Any]:
    width = max(len(item["input_ids"]) for item in items)
    input_ids, attention_mask, labels = [], [], []
    for item in items:
        padding = width - len(item["input_ids"])
        input_ids.append(item["input_ids"] + [pad_id] * padding)
        attention_mask.append(item["attention_mask"] + [0] * padding)
        labels.append(item["labels"] + [IGNORE_INDEX] * padding)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def micro_batches(
    encoded: Sequence[dict[str, list[int]]],
    *,
    micro_batch_size: int,
    seed: int,
    start_index: int,
    pad_id: int,
    torch: Any,
) -> Iterator[dict[str, Any]]:
    """Yield padded micro-batches forever, reshuffling deterministically each epoch.

    ``start_index`` is a global micro-batch counter, so a resumed run replays the
    same order without storing it.
    """
    per_epoch = max(1, len(encoded) // micro_batch_size)
    epoch = start_index // per_epoch
    offset = start_index % per_epoch
    while True:
        order = np.random.default_rng(seed + epoch).permutation(len(encoded))
        for position in range(offset, per_epoch):
            chunk = order[position * micro_batch_size : (position + 1) * micro_batch_size]
            yield pad_batch([encoded[int(i)] for i in chunk], pad_id, torch)
        offset = 0
        epoch += 1


# --------------------------------------------------------------------------- model


def build_model(config: dict[str, Any], device: str, torch: Any) -> Any:
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    repo_id, revision = load_base_pin()
    model_cfg = config["model"]
    lora_cfg = config["lora"]
    compute_dtype = getattr(torch, str(model_cfg.get("compute_dtype", "float16")))

    kwargs: dict[str, Any] = {
        "revision": revision,
        "dtype": compute_dtype,
        "device_map": {"": device},
    }
    if model_cfg.get("load_in_4bit", True):
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=str(model_cfg.get("quant_type", "nf4")),
            bnb_4bit_use_double_quant=bool(model_cfg.get("double_quant", True)),
            bnb_4bit_compute_dtype=compute_dtype,
        )
    log(f"loading {repo_id} at {revision[:8]} onto {device}")
    model = AutoModelForCausalLM.from_pretrained(repo_id, **kwargs)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    peft_config = LoraConfig(
        r=int(lora_cfg["r"]),
        lora_alpha=int(lora_cfg["alpha"]),
        lora_dropout=float(lora_cfg["dropout"]),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=list(lora_cfg["target_modules"]),
    )
    return peft_config, model


def attach_adapter(model: Any, peft_config: Any, adapter_dir: Path | None) -> Any:
    from peft import PeftModel, get_peft_model

    if adapter_dir is None:
        model = get_peft_model(model, peft_config)
    else:
        log(f"resuming adapter weights from {adapter_dir}")
        model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=True)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.train()
    return model


# --------------------------------------------------------------------------- run dir


def git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def installed_versions() -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    names = ("torch", "transformers", "peft", "bitsandbytes", "accelerate", "datasets")
    found: dict[str, str] = {"python": sys.version.split()[0]}
    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            found[name] = "absent"
    return found


def checkpoint_dirs(run_dir: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for path in run_dir.glob(f"{CHECKPOINT_PREFIX}*"):
        if not path.is_dir():
            continue
        try:
            found.append((int(path.name.removeprefix(CHECKPOINT_PREFIX)), path))
        except ValueError:
            continue
    return sorted(found)


def append_loss_row(path: Path, row: dict[str, Any]) -> None:
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(LOSS_CSV_FIELDS))
        if is_new:
            writer.writeheader()
        writer.writerow(row)


# --------------------------------------------------------------------------- hub


class HubPusher:
    def __init__(self, hub_cfg: dict[str, Any]) -> None:
        self.repo_id = hub_cfg.get("repo_id")
        self.private = bool(hub_cfg.get("private", True))
        self.enabled = bool(hub_cfg.get("push_checkpoints", False)) and bool(self.repo_id)
        self.token = os.environ.get("HF_TOKEN")
        self.reason: str | None = None
        self.api: Any = None
        if not self.enabled:
            self.reason = "push_checkpoints is off or no hub.repo_id in the config"
            return
        if not self.token:
            self.enabled = False
            self.reason = "HF_TOKEN is not set; adapters stay local"
            log(f"WARNING: skipping Hub push: {self.reason}")
            return
        try:
            from huggingface_hub import HfApi

            self.api = HfApi(token=self.token)
            self.api.create_repo(self.repo_id, private=self.private, exist_ok=True)
        except Exception as exc:  # network or auth, never fatal to training
            self.enabled = False
            self.reason = f"create_repo failed: {exc}"
            log(f"WARNING: skipping Hub push: {self.reason}")

    def push(self, folder: Path, step: int) -> None:
        if not self.enabled:
            return
        try:
            self.api.upload_folder(
                folder_path=str(folder),
                path_in_repo=f"{CHECKPOINT_PREFIX}{step}",
                repo_id=self.repo_id,
                commit_message=f"checkpoint {step}",
            )
            log(f"pushed {folder.name} to {self.repo_id}")
        except Exception as exc:
            log(f"WARNING: Hub push of {folder.name} failed, continuing: {exc}")


# --------------------------------------------------------------------------- training


def evaluate(model: Any, batches: Sequence[dict[str, Any]], device: str, torch: Any) -> float:
    if not batches:
        raise SystemExit("no validation batches: raise train.val_batches or check the val split")
    model.eval()
    total = 0.0
    with torch.no_grad():
        for batch in batches:
            moved = {name: tensor.to(device) for name, tensor in batch.items()}
            total += float(model(**moved).loss.detach().cpu())
    model.train()
    return total / len(batches)


def train(
    config: dict[str, Any],
    *,
    device: str,
    resume: bool,
    run_dir: Path,
    max_steps_override: int | None = None,
) -> dict[str, Any]:
    import torch

    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    train_cfg = config["train"]
    data_cfg = config["data"]
    micro_batch_size = int(train_cfg["micro_batch_size"])
    grad_accum = int(train_cfg["grad_accum"])
    log_every = int(train_cfg["log_every"])
    save_every = int(train_cfg["save_every"])
    val_batches_n = int(train_cfg["val_batches"])

    data_dir = resolve_path(str(data_cfg["dir"]))
    collator = AssistantOnlyCollator(max_length=int(data_cfg["max_length"]))
    pad_id = int(collator.tokenizer.pad_token_id)

    train_rows = cap_rows(
        read_jsonl(data_dir / str(data_cfg["train_file"])),
        data_cfg.get("cap_train"),
        seed,
    )
    val_rows = read_jsonl(data_dir / str(data_cfg["val_file"]))
    log(f"train rows {len(train_rows)}, val rows {len(val_rows)}, data dir {data_dir}")

    encoded_train = encode_rows(train_rows, collator, label="train")
    val_slice = val_rows[: val_batches_n * micro_batch_size]
    encoded_val = encode_rows(val_slice, collator, label="val")
    val_batches = [
        pad_batch(encoded_val[i : i + micro_batch_size], pad_id, torch)
        for i in range(0, len(encoded_val), micro_batch_size)
    ]

    steps_per_epoch = max(1, len(encoded_train) // (micro_batch_size * grad_accum))
    max_steps = max_steps_override or train_cfg.get("max_steps")
    if not max_steps:
        max_steps = steps_per_epoch * int(train_cfg.get("epochs", 1))
    max_steps = int(max_steps)

    fractions = [float(f) for f in (train_cfg.get("checkpoint_fractions") or [])]
    fraction_steps = {max(1, min(max_steps, round(max_steps * f))) for f in fractions}

    peft_config, base_model = build_model(config, device, torch)

    start_step = 0
    resume_dir: Path | None = None
    state: dict[str, Any] = {}
    if resume:
        existing = checkpoint_dirs(run_dir)
        if not existing:
            log(f"WARNING: --resume found no checkpoint in {run_dir}; starting from step 0")
        else:
            start_step, resume_dir = existing[-1]
            state = torch.load(resume_dir / "state.pt", map_location="cpu", weights_only=False)

    model = attach_adapter(base_model, peft_config, resume_dir)
    trainable = [p for p in model.parameters() if p.requires_grad]
    n_trainable = sum(p.numel() for p in trainable)
    log(f"trainable parameters {n_trainable}")

    optim_cfg = config["optim"]
    optimizer = torch.optim.AdamW(
        trainable,
        lr=float(optim_cfg["lr"]),
        weight_decay=float(optim_cfg.get("weight_decay", 0.0)),
    )
    from transformers import get_cosine_schedule_with_warmup

    warmup_steps = max(1, math.ceil(max_steps * float(optim_cfg.get("warmup_ratio", 0.03))))
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, max_steps)

    cursor = 0
    if state:
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        cursor = int(state.get("cursor", start_step * grad_accum))
        try:
            torch.set_rng_state(state["torch_rng"].cpu())
        except Exception as exc:
            log(f"WARNING: could not restore the torch RNG state: {exc}")
        log(f"resumed at step {start_step}, micro-batch cursor {cursor}")
    else:
        cursor = start_step * grad_accum

    stream = micro_batches(
        encoded_train,
        micro_batch_size=micro_batch_size,
        seed=seed,
        start_index=cursor,
        pad_id=pad_id,
        torch=torch,
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    loss_csv = run_dir / "loss.csv"
    config_json = run_dir / "config.json"
    hub = HubPusher(config.get("hub") or {})
    max_grad_norm = float(optim_cfg.get("max_grad_norm", 1.0))

    summary: dict[str, Any] = {
        "run_name": config["run_name"],
        "started_at": now_ist(),
        "device": device,
        "git_sha": git_sha(),
        "versions": installed_versions(),
        "base_model": dict(zip(("repo_id", "revision"), load_base_pin())),
        "config": config,
        "data": {
            "dir": str(data_dir),
            "train_rows": len(train_rows),
            "train_rows_encoded": len(encoded_train),
            "val_rows_encoded": len(encoded_val),
            "dropped_overlength": collator.dropped_overlength,
        },
        "steps": {
            "max_steps": max_steps,
            "steps_per_epoch": steps_per_epoch,
            "warmup_steps": warmup_steps,
            "start_step": start_step,
            "checkpoint_steps": sorted(fraction_steps),
        },
        "trainable_params": n_trainable,
        "hub": {"repo_id": hub.repo_id, "pushed": hub.enabled, "reason": hub.reason},
    }
    config_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    def save_checkpoint(step: int) -> Path:
        folder = run_dir / f"{CHECKPOINT_PREFIX}{step}"
        folder.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(folder))
        torch.save(
            {
                "step": step,
                "cursor": cursor,
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "torch_rng": torch.get_rng_state(),
            },
            folder / "state.pt",
        )
        (folder / "trainer_state.json").write_text(
            json.dumps(
                {"step": step, "cursor": cursor, "max_steps": max_steps, "saved_at": now_ist()},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        log(f"saved {folder.name}")
        hub.push(folder, step)
        return folder

    started = time.perf_counter()
    logged: dict[int, dict[str, float]] = {}
    step = start_step
    if start_step >= max_steps:
        log(f"nothing to do: checkpoint step {start_step} already reached max_steps {max_steps}")
    while step < max_steps:
        step += 1
        running = 0.0
        for _ in range(grad_accum):
            batch = next(stream)
            cursor += 1
            moved = {name: tensor.to(device) for name, tensor in batch.items()}
            loss = model(**moved).loss / grad_accum
            loss.backward()
            running += float(loss.detach().cpu())
        torch.nn.utils.clip_grad_norm_(trainable, max_grad_norm)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        if device == "mps":
            torch.mps.synchronize()

        if step % log_every == 0 or step == max_steps:
            val_loss = evaluate(model, val_batches, device, torch)
            row = {
                "step": step,
                "epoch": round(step / steps_per_epoch, 4),
                "lr": scheduler.get_last_lr()[0],
                "train_loss": round(running, 5),
                "val_loss": round(val_loss, 5),
                "elapsed_s": round(time.perf_counter() - started, 1),
                "peak_memory_gb": round(peak_memory_gb(device, torch), 2),
            }
            append_loss_row(loss_csv, row)
            logged[step] = {"train_loss": row["train_loss"], "val_loss": row["val_loss"]}
            log(
                f"step {step}/{max_steps} train {row['train_loss']:.4f} "
                f"val {row['val_loss']:.4f} lr {row['lr']:.2e} "
                f"peak {row['peak_memory_gb']} GB"
            )
            if not math.isfinite(row["train_loss"]) or not math.isfinite(row["val_loss"]):
                raise SystemExit(f"loss went non-finite at step {step}; stopping")

        if step % save_every == 0 or step in fraction_steps or step == max_steps:
            save_checkpoint(step)

    summary["finished_at"] = now_ist()
    summary["wall_s"] = round(time.perf_counter() - started, 1)
    summary["peak_memory_gb"] = round(peak_memory_gb(device, torch), 2)
    summary["final_step"] = step
    summary["logged"] = logged
    config_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log(
        f"done: {step} steps in {summary['wall_s']} s, "
        f"peak {summary['peak_memory_gb']} GB, run dir {run_dir}"
    )
    return summary


def run_smoke(config: dict[str, Any], device: str, run_dir: Path) -> int:
    """20 steps, then a resume from step 10 that must reproduce steps 11 to 20."""
    tolerance = float((config.get("smoke") or {}).get("resume_tolerance", 0.05))
    resume_from = int((config.get("smoke") or {}).get("resume_from", 10))
    max_steps = int(config["train"]["max_steps"])

    log("smoke phase 1: training from scratch")
    first = train(config, device=device, resume=False, run_dir=run_dir)
    first_losses = {int(k): v for k, v in first["logged"].items()}

    for step, folder in checkpoint_dirs(run_dir):
        if step > resume_from:
            shutil.rmtree(folder)
            log(f"removed {folder.name} so --resume picks {CHECKPOINT_PREFIX}{resume_from}")

    log(f"smoke phase 2: resuming from step {resume_from}")
    second = train(config, device=device, resume=True, run_dir=run_dir)
    second_losses = {int(k): v for k, v in second["logged"].items()}

    compared = sorted(set(first_losses) & set(second_losses))
    diffs = {
        step: abs(first_losses[step]["train_loss"] - second_losses[step]["train_loss"])
        for step in compared
    }
    worst = max(diffs.values()) if diffs else float("inf")
    ok = bool(compared) and worst <= tolerance and second["final_step"] == max_steps
    report = {
        "run_dir": str(run_dir),
        "device": device,
        "resume_from": resume_from,
        "steps": max_steps,
        "tolerance": tolerance,
        "compared_steps": compared,
        "phase1_train_loss": {s: first_losses[s]["train_loss"] for s in compared},
        "resumed_train_loss": {s: second_losses[s]["train_loss"] for s in compared},
        "max_abs_diff": round(worst, 6) if diffs else None,
        "ok": ok,
        "checked_at": now_ist(),
    }
    (run_dir / "smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log(f"smoke.json written; resume match ok={ok} max_abs_diff={report['max_abs_diff']}")
    if not ok:
        log("SMOKE FAILED: the resumed run did not reproduce the original loss trajectory")
        return 1
    return 0


# --------------------------------------------------------------------------- cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "train.yaml")
    parser.add_argument("--smoke", action="store_true", help="20 steps on 64 rows plus a resume proof")
    parser.add_argument("--resume", action="store_true", help="continue from the newest checkpoint")
    parser.add_argument("--device", default=None, choices=("auto", "cuda", "mps", "cpu"))
    parser.add_argument("--data-dir", default=None, help="override data.dir")
    parser.add_argument("--cap-train", type=int, default=None, help="override data.cap_train")
    parser.add_argument("--max-steps", type=int, default=None, help="override train.max_steps")
    parser.add_argument("--run-name", default=None, help="override run_name")
    parser.add_argument("--no-push", action="store_true", help="never push to the Hub")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    config.setdefault("hub", {})
    if args.smoke:
        config = apply_smoke(config)
    if args.data_dir:
        config["data"]["dir"] = args.data_dir
    if args.cap_train is not None:
        config["data"]["cap_train"] = args.cap_train
    if args.max_steps is not None:
        config["train"]["max_steps"] = args.max_steps
    if args.run_name:
        config["run_name"] = args.run_name
    if args.no_push:
        config["hub"]["push_checkpoints"] = False

    import torch

    device = select_device(args.device or str(config.get("device", "cuda")), torch)
    run_dir = resolve_path(str(config.get("output_dir", "train/runs"))) / str(config["run_name"])
    log(f"config {args.config} device {device} run dir {run_dir}")

    if args.smoke:
        return run_smoke(config, device, run_dir)
    train(config, device=device, resume=args.resume, run_dir=run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

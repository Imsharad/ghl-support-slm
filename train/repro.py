"""Input identity and RNG state for auditable, resumable experiments."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(config: dict, paths: dict[str, Path], prompt: str,
                encoded_ids: list[str], base_pin: tuple[str, str], *,
                runtime: dict | None = None) -> dict:
    """Fingerprint actual inputs, not filenames that can silently change."""
    value = {
        "files": {name: sha256_file(path) for name, path in sorted(paths.items())},
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "encoded_ids_sha256": hashlib.sha256(json.dumps(encoded_ids).encode()).hexdigest(),
        "base_pin": list(base_pin),
        "recipe": {key: config[key] for key in ("seed", "model", "lora", "optim", "train")},
        "max_length": config["data"]["max_length"],
        "runtime": runtime or {},
    }
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return {**value, "sha256": hashlib.sha256(payload.encode()).hexdigest()}


def capture_rng(torch: Any) -> dict:
    state = {"python": random.getstate(), "numpy": np.random.get_state(),
             "torch_cpu": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    if torch.backends.mps.is_available() and hasattr(torch.mps, "get_rng_state"):
        state["torch_mps"] = torch.mps.get_rng_state()
    return state


def restore_rng(state: dict, torch: Any) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"].cpu())
    if "torch_cuda" in state:
        if not torch.cuda.is_available():
            raise ValueError("CUDA checkpoint RNG cannot be restored without CUDA")
        torch.cuda.set_rng_state_all([item.cpu() for item in state["torch_cuda"]])
    if "torch_mps" in state:
        if not torch.backends.mps.is_available():
            raise ValueError("MPS checkpoint RNG cannot be restored without MPS")
        torch.mps.set_rng_state(state["torch_mps"].cpu())


def require_same_inputs(expected: dict | None, actual: dict) -> None:
    if not expected or expected.get("sha256") != actual["sha256"]:
        raise ValueError("resume input fingerprint mismatch or missing; use a new run for changed inputs")

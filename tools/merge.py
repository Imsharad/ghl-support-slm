#!/usr/bin/env python3
"""Merge the selected PEFT adapter into the pinned fp16 base model."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import snapshot_download
from peft import PeftConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
VERSIONS_PATH = ROOT / "configs" / "versions.json"
PROMPT_PATH = ROOT / "configs" / "prompt.txt"
DEFAULT_ADAPTER_PATH = ROOT / "artifacts" / "adapter"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "merged"
TOKENIZER_FILES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "merges.txt",
    "vocab.json",
    "special_tokens_map.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="allow a network download when the pinned base is not already cached",
    )
    return parser.parse_args()


def load_base_pin() -> tuple[str, str]:
    value: Any = json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))
    try:
        base = value["base_model"]
        repo_id = base["repo_id"]
        revision = base["revision"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid base_model entry in {VERSIONS_PATH}: {exc}") from exc
    if not isinstance(repo_id, str) or not repo_id:
        raise ValueError("base_model.repo_id must be a nonempty string")
    if not isinstance(revision, str) or not revision:
        raise ValueError("base_model.revision must be a nonempty string")
    return repo_id, revision


def validate_adapter(adapter_path: Path, repo_id: str) -> None:
    if not adapter_path.is_dir():
        raise FileNotFoundError(f"adapter directory not found: {adapter_path}")
    if not (adapter_path / "adapter_config.json").is_file():
        raise FileNotFoundError(f"adapter_config.json not found in {adapter_path}")
    config = PeftConfig.from_pretrained(adapter_path)
    recorded_base = config.base_model_name_or_path
    if recorded_base and recorded_base != repo_id:
        raise ValueError(
            f"adapter records base model {recorded_base!r}; expected pinned {repo_id!r}"
        )


def ensure_output_absent(output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(
            f"output already exists: {output_path}; move or remove it before merging"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)


def merge(adapter_path: Path, output_path: Path, *, local_files_only: bool) -> None:
    repo_id, revision = load_base_pin()
    validate_adapter(adapter_path, repo_id)
    ensure_output_absent(output_path)

    print(f"base={repo_id}@{revision}")
    print(f"adapter={adapter_path}")
    print(f"output={output_path}")

    base = AutoModelForCausalLM.from_pretrained(
        repo_id,
        revision=revision,
        local_files_only=local_files_only,
        dtype=torch.float16,
        low_cpu_mem_usage=True,
        device_map="cpu",
    )
    adapted = PeftModel.from_pretrained(base, adapter_path, is_trainable=False)
    merged = adapted.merge_and_unload(safe_merge=True)
    tokenizer = AutoTokenizer.from_pretrained(
        repo_id,
        revision=revision,
        local_files_only=local_files_only,
    )

    temporary = Path(tempfile.mkdtemp(prefix=f".{output_path.name}-", dir=output_path.parent))
    try:
        merged.save_pretrained(temporary, safe_serialization=True, max_shard_size="2GB")
        tokenizer.save_pretrained(temporary)
        # Transformers may rewrite tokenizer_config.json using its current schema.
        # Preserve the tokenizer files from the exact pinned base snapshot so the
        # pinned llama.cpp converter sees the same, revision-stable inputs as C3.
        snapshot = Path(
            snapshot_download(
                repo_id,
                revision=revision,
                local_files_only=local_files_only,
                allow_patterns=list(TOKENIZER_FILES),
            )
        )
        for filename in TOKENIZER_FILES:
            source = snapshot / filename
            if source.is_file():
                shutil.copyfile(source, temporary / filename)
        shutil.copyfile(PROMPT_PATH, temporary / "prompt.txt")
        temporary.rename(output_path)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)

    print(f"saved={output_path}")
    print(f"prompt={output_path / 'prompt.txt'}")


def main() -> int:
    args = parse_args()
    merge(
        args.adapter.expanduser().resolve(),
        args.output.expanduser().resolve(),
        local_files_only=not args.allow_download,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

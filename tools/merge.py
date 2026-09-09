#!/usr/bin/env python3
"""Merge the selected PEFT adapter into the pinned fp16 base model."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import sys
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from train.render import load_system_prompt
from train.repro import sha256_file
VERSIONS_PATH = ROOT / "configs" / "versions.json"
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
    parser.add_argument("--prompt-file", type=Path,
                        help="Must match adapter prompt when recorded; required for an adapter without prompt.txt")
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
    config = json.loads((adapter_path / "adapter_config.json").read_text())
    recorded_base = config.get("base_model_name_or_path")
    if recorded_base and recorded_base != repo_id:
        raise ValueError(
            f"adapter records base model {recorded_base!r}; expected pinned {repo_id!r}"
        )
    if not (adapter_path / "adapter_model.safetensors").is_file():
        raise FileNotFoundError("adapter_model.safetensors is required")


def select_prompt(adapter_path: Path, explicit: Path | None = None) -> tuple[Path, str]:
    recorded = adapter_path / "prompt.txt"
    if explicit is None:
        if not recorded.is_file():
            raise ValueError("adapter has no prompt.txt; explicitly provide its actual training --prompt-file")
        return recorded, load_system_prompt(recorded)
    prompt = load_system_prompt(explicit)
    if recorded.is_file() and load_system_prompt(recorded) != prompt:
        raise ValueError("explicit prompt differs from the adapter's recorded training prompt")
    return explicit, prompt


def artifact_hashes(directory: Path) -> dict[str, str]:
    # state.pt contains the optimizer; it is not part of inference identity.
    return {str(path.relative_to(directory)): sha256_file(path)
            for path in sorted(directory.rglob("*")) if path.is_file() and path.name != "state.pt"}


def ensure_output_absent(output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(
            f"output already exists: {output_path}; move or remove it before merging"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)


def merge(adapter_path: Path, output_path: Path, *, local_files_only: bool,
          prompt_file: Path | None = None) -> None:
    from peft import PeftModel
    repo_id, revision = load_base_pin()
    validate_adapter(adapter_path, repo_id)
    prompt_path, prompt = select_prompt(adapter_path, prompt_file)
    input_hashes = artifact_hashes(adapter_path)
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
        if artifact_hashes(adapter_path) != input_hashes or load_system_prompt(prompt_path) != prompt:
            raise ValueError("adapter or prompt changed during merge")
        shutil.copyfile(prompt_path, temporary / "prompt.txt")
        provenance = {
            "schema": 1, "base_model": {"repo_id": repo_id, "revision": revision},
            "adapter_files_sha256": input_hashes,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "merge_dtype": "float16", "safe_merge": True,
            "merge_code_sha256": sha256_file(Path(__file__)),
            "output_files_sha256": artifact_hashes(temporary),
        }
        (temporary / "merge_manifest.json").write_text(json.dumps(provenance, indent=2) + "\n")
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
        prompt_file=args.prompt_file.expanduser().resolve() if args.prompt_file else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

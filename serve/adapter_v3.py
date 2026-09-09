"""Load the v3 PEFT adapter on its pinned base for one support query.

This is a direct Transformers compatibility route. The scored deployment is Q8
through Ollama; numerical equality between the backends is not promised.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--device", choices=("cpu", "mps", "cuda", "auto"), default="auto")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    if not args.query.strip():
        parser.error("query must not be empty")
    from tools.merge import load_base_pin, select_prompt, validate_adapter
    from train.render import load_system_prompt
    from eval.run import TransformersRunner
    repo_id, revision = load_base_pin()
    validate_adapter(args.adapter, repo_id)
    _, prompt = select_prompt(args.adapter)
    if prompt != load_system_prompt(ROOT / "configs/prompt-v3.txt"):
        raise ValueError("this entrypoint requires the exact v3 adapter prompt")
    if args.allow_download:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id, revision=revision,
                          allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja"])
    runner = TransformersRunner(model="tuned", requested_device=args.device,
                                adapter_dir=args.adapter, system_prompt=prompt)
    print(json.dumps(asdict(runner(args.query)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

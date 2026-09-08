"""Verify an extracted training-only bundle, then run its CUDA smoke or training.

Install the pinned environment first: uv sync --frozen --extra train
This script does not provision resources, add funds, or upload/publish artifacts.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path) -> dict:
    manifest = json.loads((root / "BUNDLE_MANIFEST.json").read_text())
    if manifest.get("schema") != 1 or not manifest.get("files"):
        raise ValueError("invalid bundle manifest")
    for name, expected in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"invalid bundle file: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"bundle file hash mismatch: {name}")
    if manifest["config"] not in manifest["files"]:
        raise ValueError("bundle config is not covered by the manifest")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--train", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    manifest = verify(ROOT)
    print(f"verified {len(manifest['files'])} files from {manifest['git_sha']}", flush=True)
    if args.verify_only:
        return
    if args.resume and args.smoke:
        parser.error("smoke already includes its own resume proof")
    import torch
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required; this entry point never substitutes full local CPU/MPS training")
    if torch.cuda.device_count() != 1:
        raise SystemExit("this recipe expects exactly one visible CUDA GPU")
    print(json.dumps({"gpu": torch.cuda.get_device_name(), "torch": torch.__version__,
                      "cuda": torch.version.cuda}), flush=True)
    import yaml
    config = yaml.safe_load((ROOT / manifest["config"]).read_text())
    if config.get("hub", {}).get("push_checkpoints"):
        raise SystemExit("publication must remain disabled")
    if args.train:
        smoke_name = config.get("smoke", {}).get("run_name", f"smoke-{config['run_name']}")
        smoke_dir = ROOT / config.get("output_dir", "train/runs") / smoke_name
        subprocess.run([sys.executable, str(ROOT / "tools/check_run.py"), str(smoke_dir),
                        "--require-smoke", "--no-generate"], check=True, cwd=ROOT)
        # The smoke's resolved recipe differs intentionally; its original bundle
        # identity must still match this exact launch source.
        summary = json.loads((smoke_dir / "config.json").read_text())
        if summary.get("bundle_sha256") != hashlib.sha256((ROOT / "BUNDLE_MANIFEST.json").read_bytes()).hexdigest():
            raise SystemExit("smoke was not made from this exact bundle")
    from huggingface_hub import snapshot_download
    base = json.loads((ROOT / "configs/versions.json").read_text())["base_model"]
    snapshot_download(base["repo_id"], revision=base["revision"],
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"])
    command = [sys.executable, str(ROOT / "train/train.py"), "--config", manifest["config"], "--no-push"]
    if args.smoke:
        command.append("--smoke")
    if args.resume:
        command.append("--resume")
    subprocess.run(command, check=True, cwd=ROOT)


if __name__ == "__main__":
    main()

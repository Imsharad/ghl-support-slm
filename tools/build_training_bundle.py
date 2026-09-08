"""Create a deterministic, training-only ZIP: no credentials or final test data."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from train.repro import sha256_file


def inside(root: Path, path: Path) -> Path:
    path = path if path.is_absolute() else root / path
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"bundle source escapes repository or is a symlink: {path}")
    if not path.is_file():
        raise ValueError(f"bundle source missing: {path}")
    return path


def bundle_sources(root: Path, config_path: Path) -> list[Path]:
    config_path = inside(root, config_path)
    config = yaml.safe_load(config_path.read_text())
    if config.get("hub", {}).get("push_checkpoints"):
        raise ValueError("bundle must disable Hub publication")
    if not config.get("strict_reproducibility"):
        raise ValueError("bundle requires strict run fingerprints")
    data = config["data"]
    data_dir = Path(data["dir"])
    if data_dir.is_absolute() or Path(config["prompt_file"]).is_absolute():
        raise ValueError("bundle configuration must use repository-relative paths")
    manifest_path = inside(root, data_dir / "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    paths = [config_path, manifest_path]
    for split in ("train", "val"):
        path = inside(root, data_dir / data[f"{split}_file"])
        if sha256_file(path) != manifest["output_sha256"][split]:
            raise ValueError(f"corpus manifest mismatch: {split}")
        paths.append(path)
    for name in ("pyproject.toml", "uv.lock", "README.md", "configs/versions.json", "configs/prompt.txt",
                 config["prompt_file"], "data/prepare.py", "tools/check_run.py", "tools/run_training_bundle.py"):
        paths.append(inside(root, Path(name)))
    paths.extend(inside(root, path) for path in sorted((root / "train").glob("*.py")))
    # Only whitelisted files, never a recursive repository or home-directory copy.
    return sorted(set(paths), key=lambda p: str(p.relative_to(root)))


def create_bundle(root: Path, config_path: Path, output: Path, commit: str) -> dict:
    if output.exists():
        raise ValueError("refusing to overwrite a training bundle")
    sources = bundle_sources(root, config_path)
    config_path = inside(root, config_path)
    manifest = {"schema": 1, "git_sha": commit,
                "config": str(config_path.relative_to(root)),
                "files": {str(p.relative_to(root)): sha256_file(p) for p in sources},
                "scope": "Training code, train/validation corpus, pinned environment; final evaluation excluded",
                "spending_authority": "None. Bundle creation does not authorize provisioning or paid services."}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sources:
            info = zipfile.ZipInfo(str(path.relative_to(root)), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("BUNDLE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return {"output": str(output), "sha256": sha256_file(output), "bytes": output.stat().st_size,
            "files": len(sources), "git_sha": commit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
    if status.strip():
        raise SystemExit("commit the verified worktree before building an immutable launch bundle")
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    print(json.dumps(create_bundle(ROOT, args.config, args.output, commit), indent=2))


if __name__ == "__main__":
    main()

"""Convert a manifest-verified merged adapter to Q8 and record export lineage."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.merge import artifact_hashes
from train.repro import sha256_file


def verify_merged(directory: Path, versions: dict) -> dict:
    manifest = json.loads((directory / "merge_manifest.json").read_text())
    expected_base = {key: versions["base_model"][key] for key in ("repo_id", "revision")}
    if manifest.get("base_model") != expected_base or manifest.get("safe_merge") is not True:
        raise ValueError("merge does not record the pinned base and safe merge")
    actual = artifact_hashes(directory)
    actual.pop("merge_manifest.json", None)
    if manifest.get("output_files_sha256") != actual:
        raise ValueError("merged files differ from the merge manifest")
    if not manifest.get("adapter_files_sha256", {}).get("adapter_model.safetensors"):
        raise ValueError("missing selected adapter identity")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sidecar = args.output.with_suffix(args.output.suffix + ".export.json")
    if args.output.exists() or sidecar.exists():
        parser.error("output or lineage already exists; choose a new path")
    versions = json.loads((ROOT / "configs/versions.json").read_text())
    merge = verify_merged(args.merged, versions)
    before = artifact_hashes(args.merged)
    script = ROOT / "tools/convert.sh"
    script_hash = sha256_file(script)
    subprocess.run(["sh", str(script), str(args.merged.resolve()), str(args.output.resolve())], check=True, cwd=ROOT)
    if artifact_hashes(args.merged) != before or sha256_file(script) != script_hash:
        raise ValueError("conversion inputs changed; preserve output but do not trust it")
    checkout = ROOT / ".scratch/llama.cpp"
    converter = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if converter != versions["llama_cpp_converter"]["commit"]:
        raise ValueError("converter revision changed")
    environment = subprocess.check_output(["uv", "pip", "freeze", "--python",
                                           str(checkout / ".venv-convert/bin/python")], text=True)
    report = {"schema": 1, "base_model": merge["base_model"],
              "adapter_files_sha256": merge["adapter_files_sha256"], "prompt_sha256": merge["prompt_sha256"],
              "merge_manifest_sha256": before["merge_manifest.json"], "merged_files_sha256": before,
              "quantization": "Q8_0", "converter_commit": converter,
              "conversion_script_sha256": script_hash, "wrapper_sha256": sha256_file(Path(__file__)),
              "converter_environment": environment.splitlines(),
              "gguf_sha256": sha256_file(args.output), "gguf_bytes": args.output.stat().st_size}
    with sidecar.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"gguf": str(args.output), "lineage": str(sidecar), "sha256": report["gguf_sha256"]}))


if __name__ == "__main__":
    main()

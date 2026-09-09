"""Run only development inference on a completed candidate04 Colab training run.

Upload alongside the commit-pinned development ZIP and colab_candidate04.py.
No final queries, judges, API charges, or automatic checkpoint selection.
"""

import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

try:
    from tools.evaluation.colab_candidate04 import ROOT, digest, run
except ModuleNotFoundError:
    from colab_candidate04 import ROOT, digest, run

ADDON = Path("/content/v3-candidate04-development-dda625f.zip")
ADDON_SHA = "7da1e3a3efc5132f236f25c7ff1ac2b7f30aa8ce06159176a353905adcc2f8bc"
FILES = {"eval/run.py", "eval/blind.py", "configs/evaluation/eval.yaml",
         "eval/v3/development-boundaries-01.jsonl"}


def install_addon(path, root, expected_sha=ADDON_SHA):
    if digest(path) != expected_sha:
        raise ValueError("development addon hash mismatch")
    with zipfile.ZipFile(path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if len(members) != len(FILES) or {info.filename for info in members} != FILES:
            raise ValueError("development addon whitelist mismatch")
        if archive.testzip() is not None:
            raise ValueError("development addon CRC failure")
        # Check every existing target before creating any files. Never alter a
        # differing file, symlink or training input in the extracted bundle.
        for info in members:
            dest = root / info.filename
            if not dest.resolve().is_relative_to(root.resolve()) or dest.is_symlink():
                raise ValueError("unsafe addon destination")
            if dest.exists() and dest.read_bytes() != archive.read(info):
                raise ValueError("preserve differing existing addon file")
        for info in members:
            dest = root / info.filename
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as handle:
                    handle.write(archive.read(info))


def main():
    if platform.system() != "Linux" or not Path("/content").is_dir():
        raise SystemExit("Colab CUDA development runner; no local fallback.")
    install_addon(ADDON, ROOT)
    python = str(ROOT / ".venv/bin/python")
    log = ROOT / "colab-development.log"
    run([python, str(ROOT / "tools/training/check_run.py"),
         str(ROOT / "train/runs/v3-candidate04-t4"), "--no-generate"], log)
    # The existing runner fingerprints inputs and resumes only matching rows.
    # No safety judgments or model-selection decision are automated here.
    for model_name, step in [("base", None)] + [("tuned", s) for s in (30, 60, 90, 120)]:
        for split, source in (("val", "data/processed/v3-candidate04/val.jsonl"),
                              ("boundaries", "eval/v3/development-boundaries-01.jsonl")):
            label = model_name if step is None else f"tuned-{step}"
            output = f"eval/results/candidate04/{label}-{split}.jsonl"
            command = [python, "-m", "eval.run", "--model", model_name,
                       "--backend", "transformers", "--device", "cuda", "--split", "dev",
                       "--input", source, "--prompt-file", "configs/prompt-v3.txt",
                       "--output", output, "--check-complete"]
            if step is not None:
                command += ["--adapter", f"train/runs/v3-candidate04-t4/checkpoint-{step}"]
            run(command, log)
    output = Path("/content/ghl-candidate04-development.zip")
    if output.exists():
        raise SystemExit("Preserve existing development archive; refusing overwrite.")
    results = sorted((ROOT / "eval/results/candidate04").glob("*.json*"))
    if len(results) != 20:
        raise ValueError("Expected 10 generation files and 10 manifests")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in results + [log]:
            archive.write(path, str(path.relative_to(ROOT)))
    print(json.dumps({"archive": str(output), "sha256": digest(output),
                      "bytes": output.stat().st_size, "status": "development_generations_complete"}), flush=True)


if __name__ == "__main__":
    main()

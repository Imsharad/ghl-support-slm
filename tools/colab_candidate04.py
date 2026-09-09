"""Browser-Colab launcher for the already verified candidate04 bundle.

Upload this file and v3-candidate04-dda625f.zip to /content, then run
%run /content/colab_candidate04.py setup
Follow with smoke, train, and package as separate inspected notebook cells.
No provisioning, paid services, publishing, credentials or model changes.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile

BUNDLE = Path("/content/v3-candidate04-dda625f.zip")
BUNDLE_SHA = "2b2f144ec7be3e62b58179b84729d28850a4ed59235fc058ead754293255d5f5"
ROOT = Path("/content/ghl-candidate04")
RECOVERY = Path("/content/ghl-candidate04-recovery.tar.gz")


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def extract_bundle(bundle, output, expected_sha=BUNDLE_SHA):
    if digest(bundle) != expected_sha:
        raise ValueError("uploaded bundle SHA-256 mismatch")
    if output.exists():
        raise ValueError("preserve existing runtime directory; setup is not an overwrite operation")
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate bundle member")
        for info in archive.infolist():
            parts = PurePosixPath(info.filename)
            if (parts.is_absolute() or ".." in parts.parts
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError("unsafe bundle member")
        if archive.testzip() is not None:
            raise ValueError("bundle CRC failure")
        archive.extractall(output)


def run(command, log):
    """Retain actual stdout/stderr as well as notebook output, never environment."""
    print("RUN", " ".join(map(str, command)), flush=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write("RUN " + " ".join(map(str, command)) + "\n")
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            handle.write(line)
            handle.flush()
            print(line, end="", flush=True)
        if process.wait():
            raise subprocess.CalledProcessError(process.returncode, command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("setup", "smoke", "train", "package"))
    args = parser.parse_args()
    if platform.system() != "Linux" or not Path("/content").is_dir():
        raise SystemExit("This launcher is for a Colab Linux runtime, never local full training.")
    if args.mode == "setup":
        extract_bundle(BUNDLE, ROOT)
    if not (ROOT / "BUNDLE_MANIFEST.json").is_file():
        raise SystemExit("Run setup with the verified bundle first.")
    log = ROOT / f"colab-{args.mode}.log"
    run([sys.executable, str(ROOT / "tools/run_training_bundle.py"), "--verify-only"], log)
    if args.mode == "setup":
        run([sys.executable, str(ROOT / "tools/check_cuda_host.py"), "--volume", "/content"], log)
        run([sys.executable, "-m", "pip", "install", "--quiet", "uv==0.8.8"], log)
        uv = shutil.which("uv")
        if not uv:
            raise SystemExit("uv executable was not installed")
        run([uv, "sync", "--frozen", "--extra", "train", "--python", "3.11.11"], log)
        run([str(ROOT / ".venv/bin/python"), "-c",
             "import sys,torch; print(sys.version); print(torch.__version__,torch.version.cuda); "
             "assert torch.cuda.is_available(); x=torch.ones((8,8),device='cuda',dtype=torch.float16); "
             "assert torch.equal(x@x,torch.full_like(x,8)); print('CUDA_KERNEL_OK')"], log)
    elif args.mode in ("smoke", "train"):
        run([str(ROOT / ".venv/bin/python"), str(ROOT / "tools/run_training_bundle.py"),
             "--" + args.mode], log)
    elif args.mode == "package":
        run([str(ROOT / ".venv/bin/python"), str(ROOT / "tools/check_run.py"),
             str(ROOT / "train/runs/v3-candidate04-t4"), "--no-generate"], log)
        if RECOVERY.exists():
            raise SystemExit("Preserve existing recovery archive; refusing overwrite.")
        with tarfile.open(RECOVERY, "x:gz") as archive:
            for relative in ("train/runs/v3-candidate04-t4", "train/runs/v3-candidate04-t4-smoke",
                             "BUNDLE_MANIFEST.json", "colab-setup.log", "colab-smoke.log", "colab-train.log"):
                archive.add(ROOT / relative, arcname=relative)
        print(json.dumps({"archive": str(RECOVERY), "bytes": RECOVERY.stat().st_size,
                          "sha256": digest(RECOVERY)}), flush=True)
    print("COMPLETE", args.mode, flush=True)


if __name__ == "__main__":
    main()

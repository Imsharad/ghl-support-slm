"""Resume candidate04 development inference on local MPS, never training.

uv run --frozen --extra serve --with peft==0.20.0 --with accelerate==1.14.0 \
  python tools/candidate04_development_local.py

Keeps the interrupted CUDA comparison separate. Each complete local comparison
uses the same base revision, inputs, prompt, decoding, runner, and MPS backend.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "eval/results/v3/development/candidate04-mps"
EXPECTED = {
    "eval/run.py": "0748bd0e5a11cff4c503978691b90877fe131fb95d69b4e0cadbef89fece58fb",
    "configs/prompt-v3.txt": "fb45ab8d4a58a83fb3d0541abb350bbe6ee20a666c1b5703ea0c771f029b82ce",
    "data/processed/v3-candidate04/val.jsonl": "3e4e864b1583a781f3747140102077f53bbd0b9734ce3e689c28d16a125c2b80",
    "eval/v3/development-boundaries-01.jsonl": "b6e574a641bf409a744f6c67c776884477a4e352c38badfa349b311443b0c13a",
}


def commands(python):
    for model, step in [("base", None)] + [("tuned", n) for n in (30, 60, 90, 120)]:
        for split, source in (("boundaries", "eval/v3/development-boundaries-01.jsonl"),
                              ("val", "data/processed/v3-candidate04/val.jsonl")):
            label = model if step is None else f"tuned-{step}"
            result = OUTPUT / f"{label}-{split}.jsonl"
            command = [python, "-u", "-m", "eval.run", "--model", model,
                       "--backend", "transformers", "--device", "mps", "--split", "dev",
                       "--input", source, "--prompt-file", "configs/prompt-v3.txt",
                       "--output", str(result), "--check-complete"]
            if step is not None:
                command += ["--adapter", f"train/runs/v3-candidate04-t4/checkpoint-{step}"]
            yield command


def verify_inputs():
    for name, expected in EXPECTED.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Input changed: {name}")
    evidence = json.loads((ROOT / "data/v3/candidate04_colab_execution.json").read_text())
    for step, expected in evidence["adapter_sha256"].items():
        path = ROOT / f"train/runs/v3-candidate04-t4/checkpoint-{step}/adapter_model.safetensors"
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Recovered adapter changed: {step}")


def main():
    import torch
    if not torch.backends.mps.is_available():
        raise SystemExit("MPS unavailable; no implicit CPU or paid-remote fallback")
    verify_inputs()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "execution.log").open("a") as log:
        for command in commands(sys.executable):
            description = "RUN " + " ".join(command)
            print(description, flush=True)
            log.write(description + "\n")
            log.flush()
            process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            if process.wait():
                raise subprocess.CalledProcessError(process.returncode, command)
    verify_inputs()
    print("COMPLETE: all 330 MPS development responses; quality review still required", flush=True)


if __name__ == "__main__":
    main()

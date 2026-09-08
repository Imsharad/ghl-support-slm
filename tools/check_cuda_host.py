"""Read-only Linux/CUDA host preflight, runnable before installing training dependencies.

This checks necessary conditions, not training correctness or provider billing.
Driver floors: https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html
"""

import argparse
import csv
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tomllib


def cuda_requirement(lock: dict) -> tuple[str, int]:
    versions = {p["version"] for p in lock["package"] if p["name"] == "cuda-toolkit"}
    if len(versions) != 1:
        raise ValueError("expected exactly one pinned cuda-toolkit version")
    version = versions.pop()
    major = int(version.split(".")[0])
    floors = {12: 525, 13: 580}
    if major not in floors:
        raise ValueError("unreviewed CUDA major version; check NVIDIA compatibility requirements")
    return version, floors[major]


def validate_host(lock: dict, system: str, machine: str, gpu_csv: str,
                  free_bytes: int, min_free_gib: float = 25) -> dict:
    if min_free_gib < 25:
        raise ValueError("this launch requires at least 25 GiB free for environment/cache/checkpoints")
    if system != "Linux" or machine != "x86_64":
        raise ValueError("training host must be Linux x86_64; no local Mac fallback")
    cuda, driver_floor = cuda_requirement(lock)
    rows = list(csv.reader(gpu_csv.strip().splitlines(), skipinitialspace=True))
    if len(rows) != 1 or len(rows[0]) != 3:
        raise ValueError("expected exactly one GPU: driver_version,memory.total,name")
    driver, memory, name = (value.strip() for value in rows[0])
    if int(driver.split(".")[0]) < driver_floor:
        raise ValueError(f"CUDA {cuda} requires driver >= {driver_floor}; found {driver}")
    memory_mib = int(memory)
    if memory_mib < 14 * 1024:
        raise ValueError("candidate03 launch requires at least 14 GiB GPU memory")
    if free_bytes < min_free_gib * 1024**3:
        raise ValueError(f"need {min_free_gib:g} GiB free on the training volume")
    return {"status": "necessary_host_checks_passed", "system": system, "machine": machine,
            "locked_cuda_toolkit": cuda, "minimum_driver_major": driver_floor,
            "driver": driver, "gpu": name, "gpu_memory_mib": memory_mib,
            "volume_free_bytes": free_bytes,
            "limitations": "Not a CUDA kernel, QLoRA, persistence, budget or shutdown test"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path(__file__).resolve().parents[1] / "uv.lock")
    parser.add_argument("--volume", type=Path, required=True)
    args = parser.parse_args()
    if not args.volume.is_dir():
        parser.error("--volume must be an existing training-volume directory")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        parser.error("training host must be Linux x86_64; no local Mac fallback")
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version,memory.total,name",
                                   "--format=csv,noheader,nounits"], text=True, timeout=20)
    result = validate_host(tomllib.loads(args.lock.read_text()), platform.system(), platform.machine(),
                           gpu, shutil.disk_usage(args.volume).free)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

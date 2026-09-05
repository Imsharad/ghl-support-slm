#!/usr/bin/env python3
"""Plot train and validation loss from a run's loss.csv into curves.png.

Usage:
    uv run python train/plot_curves.py train/runs/ghl-support-qlora
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def read_series(loss_csv: Path) -> tuple[list[int], list[float], list[int], list[float], list[float]]:
    steps: list[int] = []
    train: list[float] = []
    val_steps: list[int] = []
    val: list[float] = []
    lrs: list[float] = []
    with loss_csv.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            step = int(row["step"])
            steps.append(step)
            train.append(float(row["train_loss"]))
            lrs.append(float(row["lr"]))
            raw = (row.get("val_loss") or "").strip()
            if raw:
                val_steps.append(step)
                val.append(float(raw))
    return steps, train, val_steps, val, lrs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None, help="default: <run_dir>/curves.png")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    loss_csv = run_dir / "loss.csv"
    if not loss_csv.is_file():
        print(f"loss.csv not found: {loss_csv}", file=sys.stderr)
        return 1

    steps, train, val_steps, val, lrs = read_series(loss_csv)
    if not steps:
        print(f"{loss_csv} has no rows", file=sys.stderr)
        return 1

    output = args.output or (run_dir / "curves.png")
    figure, (loss_axis, lr_axis) = plt.subplots(
        2, 1, figsize=(8, 6), sharex=True, height_ratios=[3, 1]
    )
    loss_axis.plot(steps, train, label="train", linewidth=1.4)
    if val_steps:
        loss_axis.plot(val_steps, val, label="validation", linewidth=1.4, marker="o", markersize=3)
    loss_axis.set_ylabel("loss")
    loss_axis.set_title(f"{run_dir.name}: assistant-only loss")
    loss_axis.grid(alpha=0.3)
    loss_axis.legend()

    lr_axis.plot(steps, lrs, color="tab:gray", linewidth=1.2)
    lr_axis.set_ylabel("lr")
    lr_axis.set_xlabel("optimizer step")
    lr_axis.grid(alpha=0.3)

    figure.tight_layout()
    figure.savefig(output, dpi=150)
    print(f"wrote {output} from {len(steps)} logged steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

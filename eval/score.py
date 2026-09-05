#!/usr/bin/env python3
"""Unblind a completed human score sheet and compute the final paired verdict."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "eval" / "results"
SHEET_PATH = RESULTS_DIR / "blind-sheet.csv"
KEY_PATH = RESULTS_DIR / "blind-key.json"
N_BOOT = 2000
SEED = 42
REQUIRED_COLUMNS = {
    "item_id",
    "query",
    "facts",
    "answer_A",
    "answer_B",
    "pass_A",
    "pass_B",
    "critical_A",
    "critical_B",
    "preferred",
    "notes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--sheet", type=Path, default=SHEET_PATH)
    parser.add_argument("--key", type=Path, default=KEY_PATH)
    parser.add_argument("--scores", type=Path, default=RESULTS_DIR / "scores.jsonl")
    parser.add_argument("--summary", type=Path, default=RESULTS_DIR / "summary.jsonl")
    parser.add_argument("--failures", type=Path, default=RESULTS_DIR / "failures.jsonl")
    parser.add_argument("--n-boot", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def answer_sha256(answer: str) -> str:
    return hashlib.sha256(answer.encode("utf-8")).hexdigest()


def load_key(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("blind key must be a schema_version 1 object")
    items = value.get("items")
    if not isinstance(items, dict) or not items:
        raise ValueError("blind key items must be a nonempty object")
    return value


def load_sheet(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(f"score sheet missing columns: {missing}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("score sheet is empty")
    ids = [row["item_id"] for row in rows]
    if any(not item_id for item_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("score sheet item ids must be nonempty and unique")
    return rows


def parse_bool(value: str, field: str, item_id: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"{item_id}: {field} must be true or false")


def unblind(
    sheet_rows: list[dict[str, str]],
    key: dict[str, Any],
    *,
    require_complete: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key_items = key["items"]
    sheet_ids = {row["item_id"] for row in sheet_rows}
    key_ids = set(key_items)
    if sheet_ids != key_ids:
        raise ValueError(
            f"score sheet/key id mismatch: missing={sorted(key_ids - sheet_ids)} "
            f"extra={sorted(sheet_ids - key_ids)}"
        )

    scores: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    incomplete: list[str] = []
    for row in sheet_rows:
        item_id = row["item_id"]
        item_key = key_items[item_id]
        if not isinstance(item_key, dict):
            raise ValueError(f"blind key item {item_id} is not an object")
        models = {item_key.get("model_A"), item_key.get("model_B")}
        if models != {"base", "tuned"}:
            raise ValueError(f"{item_id}: blind key must map A/B to base and tuned")
        for side in ("A", "B"):
            expected_sha = item_key.get(f"answer_{side}_sha256")
            actual_sha = answer_sha256(row[f"answer_{side}"])
            if actual_sha != expected_sha:
                raise ValueError(f"{item_id}: answer_{side} order/content does not match blind key")

        required_values = [
            row["pass_A"],
            row["pass_B"],
            row["critical_A"],
            row["critical_B"],
            row["preferred"],
        ]
        if any(not value.strip() for value in required_values):
            incomplete.append(item_id)
            continue
        side_scores: dict[str, dict[str, Any]] = {}
        for side in ("A", "B"):
            passed = parse_bool(row[f"pass_{side}"], f"pass_{side}", item_id)
            critical = parse_bool(row[f"critical_{side}"], f"critical_{side}", item_id)
            if passed and critical:
                raise ValueError(f"{item_id}: side {side} cannot pass with a critical failure")
            model = str(item_key[f"model_{side}"])
            side_scores[model] = {
                "pass": passed,
                "critical": critical,
                "answer": row[f"answer_{side}"],
            }
        preferred_side = row["preferred"].strip()
        if preferred_side not in {"A", "B", "tie"}:
            raise ValueError(f"{item_id}: preferred must be A, B, or tie")
        preferred = (
            "tie" if preferred_side == "tie" else str(item_key[f"model_{preferred_side}"])
        )
        common = {
            "id": item_id,
            "intent": str(item_key.get("intent") or "unknown"),
            "kind": str(item_key.get("kind") or "unknown"),
            "preferred": preferred,
            "notes": row["notes"],
        }
        for model in ("base", "tuned"):
            scores.append(
                {
                    **common,
                    "model": model,
                    "pass": side_scores[model]["pass"],
                    "critical": side_scores[model]["critical"],
                }
            )
        paired.append(
            {
                **common,
                "query": row["query"],
                "facts": row["facts"],
                "base": side_scores["base"],
                "tuned": side_scores["tuned"],
            }
        )

    if incomplete and require_complete:
        raise ValueError(f"incomplete score rows: {incomplete}")
    if not paired:
        raise ValueError("no complete score rows")
    return scores, paired


def paired_bootstrap(
    base_pass: list[bool],
    tuned_pass: list[bool],
    *,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float, float]:
    if len(base_pass) != len(tuned_pass) or not base_pass:
        raise ValueError("paired bootstrap requires nonempty equal-length inputs")
    if n_boot < 1:
        raise ValueError("n_boot must be positive")
    differences = np.asarray(tuned_pass, dtype=np.float64) - np.asarray(
        base_pass, dtype=np.float64
    )
    point = float(differences.mean() * 100)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(differences), size=(n_boot, len(differences)))
    samples = differences[indices].mean(axis=1) * 100
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return point, float(lo), float(hi)


def breakdown(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)
    output: dict[str, dict[str, Any]] = {}
    for label, items in sorted(grouped.items()):
        base = [bool(item["base"]["pass"]) for item in items]
        tuned = [bool(item["tuned"]["pass"]) for item in items]
        output[label] = {
            "n": len(items),
            "base_pass_rate": float(np.mean(base)),
            "tuned_pass_rate": float(np.mean(tuned)),
            "diff_points": float((np.mean(tuned) - np.mean(base)) * 100),
            "base_critical": sum(bool(item["base"]["critical"]) for item in items),
            "tuned_critical": sum(bool(item["tuned"]["critical"]) for item in items),
        }
    return output


def summarize(
    paired: list[dict[str, Any]],
    *,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    base_pass = [bool(item["base"]["pass"]) for item in paired]
    tuned_pass = [bool(item["tuned"]["pass"]) for item in paired]
    diff, lo, hi = paired_bootstrap(base_pass, tuned_pass, n_boot=n_boot, seed=seed)
    base_critical = sum(bool(item["base"]["critical"]) for item in paired)
    tuned_critical = sum(bool(item["tuned"]["critical"]) for item in paired)
    if diff >= 5 and lo > 0 and tuned_critical <= base_critical:
        verdict = "positive"
    elif diff < 0 or tuned_critical > base_critical:
        verdict = "negative"
    else:
        verdict = "inconclusive"
    return {
        "n": len(paired),
        "base_pass_rate": float(np.mean(base_pass)),
        "tuned_pass_rate": float(np.mean(tuned_pass)),
        "diff_points": diff,
        "ci95": [lo, hi],
        "base_critical": base_critical,
        "tuned_critical": tuned_critical,
        "win": sum(item["preferred"] == "tuned" for item in paired),
        "tie": sum(item["preferred"] == "tie" for item in paired),
        "loss": sum(item["preferred"] == "base" for item in paired),
        "verdict": verdict,
        "n_boot": n_boot,
        "seed": seed,
        "per_intent": breakdown(paired, "intent"),
        "per_kind": breakdown(paired, "kind"),
    }


def failures(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "intent": item["intent"],
            "kind": item["kind"],
            "query": item["query"],
            "facts": item["facts"],
            "base_answer": item["base"]["answer"],
            "tuned_answer": item["tuned"]["answer"],
            "base_pass": item["base"]["pass"],
            "tuned_pass": item["tuned"]["pass"],
            "base_critical": item["base"]["critical"],
            "tuned_critical": item["tuned"]["critical"],
            "preferred": item["preferred"],
            "notes": item["notes"],
        }
        for item in paired
        if not item["tuned"]["pass"] or item["preferred"] == "base"
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    key = load_key(args.key)
    if args.final and key.get("split") != "challenge":
        raise ValueError("--final requires a challenge blind key")
    scores, paired = unblind(
        load_sheet(args.sheet),
        key,
        require_complete=args.require_complete or args.final,
    )
    summary = summarize(paired, n_boot=args.n_boot, seed=args.seed)
    write_jsonl(args.scores, scores)
    write_jsonl(args.summary, [summary])
    failure_rows = failures(paired)
    write_jsonl(args.failures, failure_rows)
    print(
        f"n={summary['n']} base={summary['base_pass_rate']:.3f} "
        f"tuned={summary['tuned_pass_rate']:.3f} diff_points={summary['diff_points']:.2f} "
        f"ci95={summary['ci95']} verdict={summary['verdict']}"
    )
    print(f"scores={args.scores} summary={args.summary} failures={len(failure_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

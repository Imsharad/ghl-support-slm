"""Validate and assemble explicitly authored targets with immutable source provenance."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.select_targets_v3 import select
from train.collate import AssistantOnlyCollator
from train.render import load_system_prompt
from train.repro import sha256_file


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_targets(paths: list[Path]) -> dict[str, str]:
    targets = {}
    for path in paths:
        value = json.loads(path.read_text(), object_pairs_hook=unique_object)
        for key, response in value["targets"].items():
            if key in targets:
                raise ValueError(f"duplicate authored target: {key}")
            if not isinstance(response, str) or not response.strip():
                raise ValueError(f"missing target text: {key}")
            if any(token in response for token in ("<|im_start|>", "<|im_end|>", "<|endoftext|>")):
                raise ValueError(f"chat control token in target: {key}")
            targets[key] = response
    return targets


def assemble(rows: list[dict], targets: dict[str, str], collator) -> tuple[list[dict], dict]:
    expected = {r["id"] for r in rows}
    if len(expected) != len(rows) or expected != targets.keys():
        raise ValueError("target IDs must exactly match unique selected source IDs")
    output, lengths = [], []
    for row in rows:
        response = targets[row["id"]]
        # Preserve concrete long reference numbers, including leading zeros.
        references = re.findall(r"\d{3,}", row["instruction"])
        if any(ref not in response for ref in references):
            raise ValueError(f"target drops a concrete reference: {row['id']}")
        item = {k: row[k] for k in ("id", "group_id", "intent", "category", "instruction")}
        item.update(response=response, flags="BITEXT_QUERY_AUTHORED_TARGET_V3",
                    original_response=row["response"], target_source="assistant_authored_correction_v3")
        encoded = collator.encode(item)
        if encoded is None:
            raise ValueError(f"authored example exceeds token budget: {row['id']}")
        lengths.append(len(encoded["input_ids"]))
        item["n_tokens"] = lengths[-1]
        output.append(item)
    return output, {"rows": len(output), "min_tokens": min(lengths), "max_tokens": max(lengths),
                    "by_intent": dict(sorted(Counter(r["intent"] for r in output).items())),
                    "unique_target_count": len(set(targets.values()))}


def checked_augmentation(path: Path, audit_path: Path, source_manifest: dict) -> list[dict]:
    report = json.loads(audit_path.read_text())
    rows = json.loads(path.read_text(), object_pairs_hook=unique_object)["rows"]
    expected_hashes = {source_manifest["source_sha256"][s] for s in ("val", "test")}
    if (report["input_sha256"] != sha256_file(path) or not report["pass"]
            or set(report["against_sha256"].values()) != expected_hashes
            or not 0 < report["threshold"] <= .86):
        raise ValueError("augmentation audit is failed, stale, incomplete, or too permissive")
    if ({r["id"] for r in rows} != {r["id"] for r in report["results"]}
            or len({r["id"] for r in rows}) != len(rows)
            or len({r["group_id"] for r in rows}) != len(rows)
            or any(not r["pass"] or r["max_cosine"] >= .86 or r["shared_sixgrams"]
                   for r in report["results"])):
        raise ValueError("augmentation screening results do not match unique passing rows")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--targets-dir", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--review-note", required=True, help="Honest description of the actual target review")
    parser.add_argument("--augmentation", type=Path)
    parser.add_argument("--augmentation-audit", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("refusing to overwrite an existing corpus")
    if bool(args.augmentation) != bool(args.augmentation_audit):
        parser.error("augmentation requires both its input and passing audit")
    manifest_path = args.source_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    selection = json.loads(args.selection.read_text())
    if sha256_file(manifest_path) != selection["source_manifest_sha256"]:
        raise ValueError("selection refers to a different source manifest")
    prompt = load_system_prompt(args.prompt_file)
    collator = AssistantOnlyCollator(max_length=args.max_length, system_prompt=prompt)
    output, stats, files = {}, {}, {}
    for split in ("train", "val"):
        path = args.source_dir / f"{split}.jsonl"
        if sha256_file(path) != manifest["output_sha256"][split]:
            raise ValueError(f"source hash mismatch: {split}")
        source = [json.loads(line) for line in path.read_text().splitlines()]
        selected, excluded = select(source, selection["selection"][split]["quota"], selection["seed"])
        if [r["id"] for r in selected] != selection["selection"][split]["selected_ids"]:
            raise ValueError(f"selection cannot be reproduced: {split}")
        paths = sorted(args.targets_dir.glob("train_part*.json")) if split == "train" else [args.targets_dir / "val.json"]
        files[split] = {str(p): sha256_file(p) for p in paths}
        output[split], stats[split] = assemble(selected, load_targets(paths), collator)
    augmentation = None
    if args.augmentation:
        rows = checked_augmentation(args.augmentation, args.augmentation_audit, manifest)
        if {r["intent"] for r in rows} - stats["train"]["by_intent"].keys():
            raise ValueError("augmentation contains unknown intents")
        existing_ids = {r["id"] for pool in output.values() for r in pool}
        existing_groups = {r["group_id"] for pool in output.values() for r in pool}
        if any(r["id"] in existing_ids or r["group_id"] in existing_groups for r in rows):
            raise ValueError("augmentation collides with a source ID/group")
        augmented, augmented_stats = assemble(rows, {r["id"]: r["response"] for r in rows}, collator)
        for row in augmented:
            row.update(original_response=None, flags="SYNTH_CONTEXT_V3",
                       target_source="assistant_authored_fictional_context_v3")
        output["train"].extend(augmented)
        stats["augmentation"] = augmented_stats
        augmentation = {"input_sha256": sha256_file(args.augmentation),
                        "audit_sha256": sha256_file(args.augmentation_audit)}
    if {r["group_id"] for r in output["train"]} & {r["group_id"] for r in output["val"]}:
        raise ValueError("train/validation groups overlap")
    args.output_dir.mkdir(parents=True)
    output_hashes = {}
    for split, rows in output.items():
        path = args.output_dir / f"{split}.jsonl"
        with path.open("x") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        output_hashes[split] = sha256_file(path)
    report = {
        "schema": 1, "status": "assembled_candidate_not_yet_trained",
        "source_manifest_sha256": sha256_file(manifest_path),
        "selection_sha256": sha256_file(args.selection), "authored_target_files": files,
        "prompt_file_sha256": sha256_file(args.prompt_file), "max_length": args.max_length,
        "script_sha256": sha256_file(Path(__file__)), "output_sha256": output_hashes,
        "review_note": args.review_note, "stats": stats,
        "augmentation": augmentation, "final_rows": {s: len(r) for s, r in output.items()},
        "limitation": "Small balanced subset, assistant-authored targets and same-author validation references. Validation loss is development evidence, not independent proof of task quality. Fresh paired evaluation remains required.",
        "leakage_basis": "Bitext instruction groups are subsets of the audited source pool. Any authored augmentation has a separate holdout screening report. Target phrasing can overlap across splits and is not an independent test metric.",
    }
    with (args.output_dir / "manifest.json").open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.output_dir), "stats": stats}, indent=2))


if __name__ == "__main__":
    main()

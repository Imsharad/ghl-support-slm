"""Create a blinded v3 grading CSV and analyze complete owner-scored pairs.

This never assigns human judgments. The private key must not be shown to the
grader until the completed sheet is saved. Generation failures remain in the
denominator and cannot be scored as passes. A model/data seal is required; this
tool does not create one or choose a checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.blind import index_by_id, load_jsonl
from eval.prepare_v3 import KINDS, read_json
from eval.v3_metrics import summarize_pairs, validate_pairs
from train.repro import sha256_file
from train.render import load_system_prompt

IMMUTABLE = ("item_id", "query", "acceptable_actions", "critical_fail_if", "answer_A", "answer_B")
JUDGMENTS = tuple(f"{field}_{side}" for side in ("A", "B")
                  for field in ("pass", "critical", "credential_violation"))
COLUMNS = (*IMMUTABLE, *JUDGMENTS, "preferred", "notes")
MISSING_ANSWER = "[No answer: generation failed]"


def object_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def sheet_text(value: str) -> str:
    """Keep untrusted model text from being interpreted as a spreadsheet formula."""
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def verify_seal(seal: dict, cases_path: Path, protocol_path: Path) -> tuple[list[dict], dict]:
    if seal.get("schema") != 3 or seal.get("status") != "frozen_before_final_inference":
        raise ValueError("a v3 model/data/protocol seal is required")
    for field, path in (("challenge_sha256", cases_path), ("protocol_sha256", protocol_path),
                        ("metrics_code_sha256", ROOT / "eval/v3_metrics.py"),
                        ("grading_code_sha256", Path(__file__))):
        if seal.get(field) != sha256_file(path):
            raise ValueError(f"seal mismatch: {field}")
    protocol = read_json(protocol_path)
    if (protocol["sample_design"]["per_intent"] != 4
            or tuple(protocol["sample_design"]["scenario_types"]) != KINDS
            or protocol["analysis"]["improvement_threshold_points"] != 5):
        raise ValueError("protocol differs from the implemented fixed analysis")
    cases = load_jsonl(cases_path)
    case_by = index_by_id(cases, "final cases")
    intents = {r["intent"] for r in read_json(ROOT / "data/intents.json")}
    if len(case_by) != 108 or {r["intent"] for r in cases} != intents:
        raise ValueError("expected all 108 final cases across 27 intents")
    for intent in intents:
        selected = [r for r in cases if r["intent"] == intent]
        if len(selected) != 4 or {r["kind"] for r in selected} != set(KINDS):
            raise ValueError("incomplete per-intent scenario coverage")
    expected_decoding = dict(protocol["comparison"]["decoding"])
    expected_decoding["repeat_penalty"] = expected_decoding.pop("repetition_penalty")
    shared = seal["inference"]
    if shared.get("backend") != "ollama" or shared.get("decoding") != expected_decoding:
        raise ValueError("sealed inference differs from protocol")
    expected_prompt = load_system_prompt(ROOT / "configs/prompt-v3.txt")
    if shared.get("prompt_sha256") != hashlib.sha256(expected_prompt.encode()).hexdigest():
        raise ValueError("sealed prompt differs from the protocol's exact v3 prompt")
    if set(seal["models"]) != {"base", "tuned"}:
        raise ValueError("seal must name base and tuned identities")
    if seal["models"]["base"]["digest"] == seal["models"]["tuned"]["digest"]:
        raise ValueError("base and tuned artifacts must be distinct")
    return cases, protocol


def verify_manifest(manifest: dict, seal: dict, model: str) -> None:
    if (manifest.get("schema") != 1 or manifest.get("model") != model
            or manifest.get("split_sha256") != seal["challenge_sha256"]
            or manifest.get("identity") != seal["models"][model]):
        raise ValueError(f"{model} manifest identity or split mismatch")
    for field in ("backend", "decoding", "prompt_sha256", "runner_sha256", "render_sha256"):
        if manifest.get(field) != seal["inference"].get(field) or field not in manifest:
            raise ValueError(f"{model} manifest inference mismatch: {field}")
    prompt = manifest.get("system_prompt")
    if not isinstance(prompt, str) or hashlib.sha256(prompt.encode()).hexdigest() != manifest["prompt_sha256"]:
        raise ValueError("manifest prompt text does not match its hash")


def build_sheet(cases: list[dict], base: list[dict], tuned: list[dict], *, seed: str) -> tuple[list[dict], dict]:
    case_by = index_by_id(cases, "cases")
    raw = {"base": index_by_id(base, "base"), "tuned": index_by_id(tuned, "tuned")}
    if any(set(rows) != set(case_by) for rows in raw.values()):
        raise ValueError("raw outputs must cover all final IDs exactly")
    rng = random.Random(int(seed, 16))
    ids = list(case_by)
    rng.shuffle(ids)
    sheet, private = [], {"seed": seed, "items": {}}
    for item_id in ids:
        case = case_by[item_id]
        models = ["base", "tuned"]
        rng.shuffle(models)
        row = {"item_id": item_id, "query": sheet_text(case["query"]),
               "acceptable_actions": sheet_text("\n".join(case["acceptable_actions"])),
               "critical_fail_if": sheet_text("\n".join(case["critical_fail_if"])),
               "preferred": "", "notes": ""}
        mapping, failures = {}, {}
        for side, model in zip(("A", "B"), models):
            result = raw[model][item_id]
            if result.get("model") != model or result.get("backend") != "ollama":
                raise ValueError("raw row model/backend mismatch")
            answer = result.get("answer")
            failed = bool(result.get("error")) or not isinstance(answer, str) or not answer.strip()
            row[f"answer_{side}"] = sheet_text(MISSING_ANSWER if failed else answer)
            for field in ("pass", "critical", "credential_violation"):
                row[f"{field}_{side}"] = "false" if failed else ""
            mapping[side], failures[side] = model, failed
        private["items"][item_id] = {
            "models": mapping, "generation_failures": failures,
            "immutable_sha256": object_hash({field: row[field] for field in IMMUTABLE}),
            "intent": case["intent"], "kind": case["kind"],
        }
        sheet.append(row)
    return sheet, private


def parse_bool(value: str) -> bool:
    if value not in ("true", "false"):
        raise ValueError("every boolean judgment must be explicitly true or false")
    return value == "true"


def unblind(sheet: list[dict], key: dict) -> list[dict]:
    item_ids = [row.get("item_id") for row in sheet]
    if len(set(item_ids)) != len(item_ids) or set(item_ids) != set(key["items"]):
        raise ValueError("scored sheet must cover every key ID exactly once")
    pairs = []
    for row in sheet:
        item_id = row["item_id"]
        item = key["items"][item_id]
        if object_hash({field: row[field] for field in IMMUTABLE}) != item["immutable_sha256"]:
            raise ValueError("immutable query, rubric or answer text was changed")
        if row.get("preferred") not in ("A", "B", "tie") or not row.get("notes", "").strip():
            raise ValueError("each pair needs a preference and evidence note")
        pair = {"id": item_id, "intent": item["intent"], "kind": item["kind"],
                "preferred": item["models"].get(row["preferred"], "tie"), "notes": row["notes"]}
        for side in ("A", "B"):
            judgments = {field: parse_bool(row[f"{field}_{side}"])
                         for field in ("pass", "critical", "credential_violation")}
            if item["generation_failures"][side] and any(judgments.values()):
                raise ValueError("generation failure must retain automatic all-false judgment")
            pair[item["models"][side]] = dict(judgments, generation_failure=item["generation_failures"][side])
        pairs.append(pair)
    validate_pairs(pairs, intents={row["intent"] for row in key["items"].values()})
    return sorted(pairs, key=lambda row: row["id"])


def write_json(path: Path, value, *, private: bool = False):
    # Private key never goes into the default tracked evaluation directories.
    descriptor = path.open("x")
    if private:
        path.chmod(0o600)
    with descriptor as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("blind", "score"))
    parser.add_argument("--seal", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=ROOT / "eval/v3/protocol.json")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--tuned", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--judge", help="Name/alias of the actual human grader; never an invented attribution")
    args = parser.parse_args()
    seal = read_json(args.seal)
    cases, protocol = verify_seal(seal, args.cases, args.protocol)
    manifests = {model: path.with_suffix(path.suffix + ".manifest.json")
                 for model, path in (("base", args.base), ("tuned", args.tuned))}
    raw_paths = {"base": args.base, "tuned": args.tuned}
    raw = {}
    for model, path in raw_paths.items():
        manifest = read_json(manifests[model])
        verify_manifest(manifest, seal, model)
        if manifest.get("final_seal_sha256") != sha256_file(args.seal):
            raise ValueError("raw manifest is not bound to this final seal")
        raw[model] = load_jsonl(path)
        if any(row.get("tag") != seal["models"][model]["tag"]
               or row.get("final_seal_sha256") != sha256_file(args.seal) for row in raw[model]):
            raise ValueError("raw row tag or seal differs from the final seal")
    bindings = {"seal_sha256": sha256_file(args.seal),
                "raw_sha256": {m: sha256_file(p) for m, p in raw_paths.items()},
                "manifest_sha256": {m: sha256_file(p) for m, p in manifests.items()},
                "grading_code_sha256": sha256_file(Path(__file__))}
    if args.mode == "blind":
        if args.key.exists() or args.sheet.exists():
            parser.error("refusing to overwrite a grading sheet or private key")
        if not args.key.resolve().is_relative_to((ROOT / ".scratch").resolve()):
            parser.error("private key must be under the ignored .scratch directory")
        sheet, key = build_sheet(cases, raw["base"], raw["tuned"], seed=secrets.token_hex(32))
        key.update(schema=3, bindings=bindings)
        args.key.parent.mkdir(parents=True, exist_ok=True)
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.key, key, private=True)
        with args.sheet.open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(sheet)
        print(json.dumps({"sheet": str(args.sheet), "pairs": len(sheet), "status": "awaiting_actual_human_grading",
                          "instructions": "Fill every boolean as true/false, preference A/B/tie, and a brief evidence note. Save the completed CSV without changing query/rubric/answers. Keep the key private until scores are saved. The sealed protocol is the full rubric."}))
    else:
        if not args.judge or not args.judge.strip() or args.output_dir is None:
            parser.error("score needs --judge and a new --output-dir")
        if args.output_dir.exists():
            parser.error("refusing to overwrite prior scores")
        key = read_json(args.key)
        if key.get("schema") != 3 or key.get("bindings") != bindings:
            raise ValueError("private key input/code bindings changed")
        # Rebuild from bound raw outputs: do not trust mutable private metadata alone.
        _, replay = build_sheet(cases, raw["base"], raw["tuned"], seed=key["seed"])
        if replay["items"] != key["items"]:
            raise ValueError("private key does not replay from raw outputs")
        with args.sheet.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(COLUMNS):
                raise ValueError("scored CSV columns differ from the grading template")
            sheet = list(reader)
        pairs = unblind(sheet, key)
        result = summarize_pairs(pairs)
        result.update(bindings=bindings, scored_sheet_sha256=sha256_file(args.sheet),
                      human_judge=args.judge.strip(), judge_attestation="Owner-supplied attribution, not independently verified.",
                      generation_failures={m: sum(r[m]["generation_failure"] for r in pairs) for m in ("base", "tuned")},
                      pairs=pairs, protocol=protocol)
        args.output_dir.mkdir(parents=True)
        write_json(args.output_dir / "analysis.json", result)
        print(json.dumps({"output": str(args.output_dir / "analysis.json"), "verdict": result["verdict"],
                          "difference_points": result["difference_percentage_points"],
                          "ci95_points": result["primary_cluster_ci95_points"]}))


if __name__ == "__main__":
    main()

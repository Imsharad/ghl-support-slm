#!/usr/bin/env python3
"""Clean, group, split, and freeze the Bitext customer-support rows.

Deterministic from data/raw/bitext.csv. Writes gitignored jsonl under
data/processed/ plus data/splits.json and data/audit.json (committed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CSV_PATH = ROOT / "data" / "raw" / "bitext.csv"
GROUPING_PATH = ROOT / "configs" / "grouping.json"
CLEANING_PATH = ROOT / "configs" / "cleaning.json"
PROCESSED_DIR = ROOT / "data" / "processed"
SPLITS_PATH = ROOT / "data" / "splits.json"
AUDIT_PATH = ROOT / "data" / "audit.json"

CSV_COLUMNS = ["flags", "instruction", "category", "intent", "response"]
ROW_KEYS = [
    "id",
    "group_id",
    "intent",
    "category",
    "flags",
    "instruction",
    "response",
    "cleaning",
    "n_tokens",
]
SPLIT_NAMES = ("train", "val", "test")
SEED = 42
MAX_LENGTH = 512
NEAR_COLLAPSE_SHARE = 0.50
PLACEHOLDER_RE = re.compile(r"\{\{([^{}]+)\}\}")
FROZEN_SPLITS_COMMIT = "24ab0d9"
NUMBER_HEADS = "order|purchase|invoice|tracking|account"
NOUN_HEADS = "order|purchase|invoice|account"
ID_FRAME_NAMES = ("number", "noun", "the", "standalone")
_PURCHASE_ORDER_NUMBER = re.compile(
    r"(?i)(?P<consumed>(?:(?:\bthe|\bmy|\byour)\s+)?\bpurchase\s+order\s+number\s+)$"
)
_NUMBER_PREFIX = re.compile(
    rf"(?i)(?P<consumed>(?:(?:\bthe|\bmy|\byour)\s+)?\b(?P<head>{NUMBER_HEADS})\s+number\s+)$"
)
_BARE_NUMBER_PREFIX = re.compile(
    r"(?i)(?P<consumed>(?:(?:\bthe|\bmy|\byour)\s+)?\bnumber\s+)$"
)
_NOUN_PREFIX = re.compile(
    rf"(?i)(?P<consumed>(?:(?:\bthe|\bmy|\byour)\s+)?\b(?P<head>{NOUN_HEADS})\s+)$"
)
_THE_PREFIX = re.compile(r"(?i)(?P<consumed>\bthe)\s+$")
IST = timezone(timedelta(hours=5, minutes=30))
RESIDUAL_RISK = (
    "Average-linkage clusters at cosine distance 1 - threshold, then exact "
    "normalized-instruction and response-template unions. Embeddings and 40 "
    "labelled pairs cannot prove zero leakage: paraphrases exist below the "
    "threshold, and average linkage still allows some cross-cluster pairs "
    "above it. Cross-split group-id and normalized-instruction intersections "
    "must be empty; nearest-neighbour cosine is the residual check."
)


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_jsonl(rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    return sha256_bytes(payload.encode("utf-8"))


def normalize(text: str) -> str:
    """lower_strip_punct_keep_neg_num: same function as data/calibrate_threshold.py."""
    lowered = text.casefold()
    lowered = PLACEHOLDER_RE.sub(" ph ", lowered)
    lowered = lowered.replace("n't", " not ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def response_template(text: str) -> str:
    slotted = PLACEHOLDER_RE.sub("{{SLOT}}", text)
    return normalize(slotted)


def collapse_ws(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def placeholder_rule_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"placeholder_{slug or 'unnamed'}"


class DSU:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object")
    return value


def load_csv(path: Path = CSV_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing {path}; run data/fetch.py first")
    frame = pd.read_csv(path, keep_default_na=False)
    missing = [col for col in CSV_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"CSV missing {missing}")
    out = frame.loc[:, CSV_COLUMNS].copy()
    out["id"] = [f"bitext-{i:06d}" for i in range(len(out))]
    return out


def compile_rule(rule: dict) -> dict:
    compiled = dict(rule)
    pattern = rule.get("regex")
    if isinstance(pattern, str):
        flags = re.IGNORECASE if "i" in str(rule.get("flags", "")) else 0
        compiled["_pattern"] = re.compile(pattern, flags)
    return compiled


def load_cleaning(path: Path = CLEANING_PATH) -> dict:
    payload = load_json(path)
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{path} needs a nonempty rules list")
    payload = dict(payload)
    payload["rules"] = [compile_rule(rule) for rule in rules]
    reject_name = payload.get("placeholder_reject_name_regex", "")
    payload["_reject_name"] = re.compile(str(reject_name), re.IGNORECASE) if reject_name else None
    replace_map = payload.get("placeholder_replace", {})
    if not isinstance(replace_map, dict):
        raise ValueError("placeholder_replace must be an object")
    payload["_replace_map"] = {str(k): str(v) for k, v in replace_map.items()}
    id_style = payload.get("placeholder_id_style", [])
    if not isinstance(id_style, list):
        raise ValueError("placeholder_id_style must be a list")
    payload["_id_style"] = {str(item).casefold() for item in id_style}
    return payload


def match_field(rule: dict, instruction: str, response: str) -> str:
    field = rule.get("field", "response")
    if field == "instruction":
        return instruction
    if field == "both":
        return instruction + "\n" + response
    return response


def timeline_supplied(match: re.Match[str], instruction: str) -> bool:
    nums = re.findall(r"\d+", match.group(0))
    if not nums:
        return False
    inst_nums = set(re.findall(r"\d+", instruction))
    return all(num in inst_nums for num in nums)


def placeholder_decision(name: str, cleaning: dict) -> tuple[str, str]:
    """Return ('replace', wording) or ('reject', rule_id)."""
    mapping = cleaning["_replace_map"]
    if name in mapping:
        return "replace", mapping[name]
    reject_name = cleaning.get("_reject_name")
    if reject_name is not None and reject_name.search(name):
        return "reject", "reject_placeholder_no_neutral_wording"
    lowered = name.strip()
    if not lowered or len(lowered) > 48:
        return "reject", "reject_placeholder_no_neutral_wording"
    if re.search(r"\d", lowered) and re.search(
        r"(feature|platform|city|step|channel)", lowered, re.IGNORECASE
    ):
        return "reject", "reject_placeholder_no_neutral_wording"
    wording = "your " + lowered[0].lower() + lowered[1:]
    return "replace", wording


def id_style_phrase(mapped: str, cleaning: dict) -> str | None:
    if not mapped.lower().startswith("your "):
        return None
    phrase = mapped[5:].strip()
    if phrase.casefold() in cleaning.get("_id_style", set()):
        return phrase.casefold()
    return None


def apply_id_frame(prefix: str, possessive: str, noun_phrase: str) -> tuple[str, str, str]:
    """Consume a preceding frame and return (kept_prefix, replacement, frame_name)."""
    match = _PURCHASE_ORDER_NUMBER.search(prefix)
    if match:
        return prefix[: match.start()], f"{possessive} purchase", "noun"
    match = _NUMBER_PREFIX.search(prefix)
    if match:
        head = match.group("head").casefold()
        return prefix[: match.start()], f"{possessive} {head} number", "number"
    match = _BARE_NUMBER_PREFIX.search(prefix)
    if match:
        return prefix[: match.start()], f"{possessive} order number", "number"
    match = _NOUN_PREFIX.search(prefix)
    if match:
        head = match.group("head").casefold()
        return prefix[: match.start()], f"{possessive} {head}", "noun"
    match = _THE_PREFIX.search(prefix)
    if match:
        return prefix[: match.start()], f"{possessive} {noun_phrase}", "the"
    return prefix, f"{possessive} {noun_phrase}", "standalone"


def empty_frame_counts() -> dict[str, dict[str, int]]:
    return {
        field: {name: 0 for name in ID_FRAME_NAMES}
        for field in ("instruction", "response")
    }


def replace_placeholders(
    text: str,
    cleaning: dict,
    *,
    field: str,
    frame_counts: dict[str, dict[str, int]] | None = None,
) -> tuple[str | None, list[str], str | None]:
    applied: list[str] = []
    reject_id: str | None = None
    possessive = "my" if field == "instruction" else "your"
    counts = frame_counts[field] if frame_counts is not None else None
    pieces: list[str] = []
    last = 0
    for match in PLACEHOLDER_RE.finditer(text):
        name = match.group(1)
        action, value = placeholder_decision(name, cleaning)
        if action == "reject":
            reject_id = value
            break
        pieces.append(text[last : match.start()])
        prefix = "".join(pieces)
        phrase = id_style_phrase(value, cleaning)
        if phrase is not None:
            prefix, replacement, frame = apply_id_frame(prefix, possessive, phrase)
            if counts is not None:
                counts[frame] += 1
        elif value.lower().startswith("your "):
            other = value[5:].strip().casefold()
            the_match = _THE_PREFIX.search(prefix)
            if the_match:
                prefix = prefix[: the_match.start()]
                replacement = f"{possessive} {other}"
                if counts is not None:
                    counts["the"] += 1
            else:
                replacement = f"{possessive} {other}"
                if counts is not None:
                    counts["standalone"] += 1
        else:
            replacement = value
        applied.append(placeholder_rule_id(name))
        pieces = [prefix, replacement]
        last = match.end()
    if reject_id is not None:
        return None, applied, reject_id
    pieces.append(text[last:])
    return collapse_ws("".join(pieces)), applied, None


def apply_cleaning(
    instruction: str,
    response: str,
    cleaning: dict,
    frame_counts: dict[str, dict[str, int]] | None = None,
) -> tuple[str, str, list[str], str | None]:
    """Return cleaned instruction/response, applied rule ids, or a reject rule id."""
    applied: list[str] = []
    for rule in cleaning["rules"]:
        action = rule["action"]
        rule_id = str(rule["id"])
        if action == "reject":
            pattern = rule.get("_pattern")
            if pattern is None:
                continue
            target = match_field(rule, instruction, response)
            match = pattern.search(target)
            if match is None:
                continue
            if rule.get("unless_in_instruction") and timeline_supplied(match, instruction):
                continue
            return instruction, response, applied, rule_id
        if action == "replace_placeholders":
            new_inst, inst_rules, reject = replace_placeholders(
                instruction, cleaning, field="instruction", frame_counts=frame_counts
            )
            if reject is not None:
                return instruction, response, applied, reject
            new_resp, resp_rules, reject = replace_placeholders(
                response, cleaning, field="response", frame_counts=frame_counts
            )
            if reject is not None:
                return instruction, response, applied, reject
            instruction = new_inst or ""
            response = new_resp or ""
            applied.extend(inst_rules)
            applied.extend(resp_rules)
            if inst_rules or resp_rules:
                applied.append(rule_id)
            if not instruction or not response:
                return instruction, response, applied, "reject_empty_after_clean"
    return instruction, response, applied, None


def embed(texts: list[str], model_id: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_id)
    vectors = model.encode(
        texts,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def union_exact_and_template(dsu: DSU, norms: list[str], templates: list[str]) -> None:
    by_norm: dict[str, list[int]] = defaultdict(list)
    by_tmpl: dict[str, list[int]] = defaultdict(list)
    for i, (norm, tmpl) in enumerate(zip(norms, templates)):
        by_norm[norm].append(i)
        by_tmpl[tmpl].append(i)
    for members in by_norm.values():
        for j in members[1:]:
            dsu.union(members[0], j)
    for members in by_tmpl.values():
        for j in members[1:]:
            dsu.union(members[0], j)


def cluster_intent(
    vectors: np.ndarray,
    norms: list[str],
    templates: list[str],
    *,
    threshold: float,
    linkage: str,
) -> list[int]:
    n = len(norms)
    dsu = DSU(n)
    if n >= 2:
        from sklearn.cluster import AgglomerativeClustering

        model = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1.0 - threshold,
            metric="cosine",
            linkage=linkage,
        )
        labels = model.fit_predict(vectors)
        by_lab: dict[int, list[int]] = defaultdict(list)
        for i, lab in enumerate(labels):
            by_lab[int(lab)].append(i)
        for members in by_lab.values():
            for j in members[1:]:
                dsu.union(members[0], j)
    union_exact_and_template(dsu, norms, templates)
    return [dsu.find(i) for i in range(n)]


def assign_group_ids(
    records: list[dict],
    embeddings: np.ndarray,
    grouping: dict,
) -> tuple[list[dict], dict[str, dict]]:
    threshold = float(grouping["cosine_threshold"])
    linkage = str(grouping["linkage"])
    by_intent: dict[str, list[int]] = defaultdict(list)
    for i, rec in enumerate(records):
        by_intent[str(rec["intent"])].append(i)

    next_id = 1
    stats: dict[str, dict] = {}
    for intent in sorted(by_intent):
        idxs = by_intent[intent]
        local = embeddings[np.asarray(idxs)]
        norms = [str(records[i]["norm_instruction"]) for i in idxs]
        templates = [str(records[i]["resp_template"]) for i in idxs]
        roots = cluster_intent(
            local, norms, templates, threshold=threshold, linkage=linkage
        )
        buckets: dict[int, list[int]] = defaultdict(list)
        for local_i, root in enumerate(roots):
            buckets[root].append(idxs[local_i])
        ordered = sorted(buckets.values(), key=lambda members: min(records[i]["id"] for i in members))
        sizes = [len(members) for members in ordered]
        n_rows = len(idxs)
        largest = max(sizes) if sizes else 0
        stats[intent] = {
            "intent": intent,
            "rows": n_rows,
            "groups": len(ordered),
            "largest": largest,
            "largest_share": round(largest / n_rows, 4) if n_rows else 0.0,
            "near_collapse": bool(n_rows and largest / n_rows >= NEAR_COLLAPSE_SHARE),
            "collapsed": bool(len(ordered) == 1),
        }
        for members in ordered:
            group_id = f"g-{next_id:04d}"
            next_id += 1
            for i in members:
                records[i]["group_id"] = group_id
    return records, stats


def split_counts(n_groups: int) -> tuple[int, int, int]:
    if n_groups <= 0:
        return 0, 0, 0
    if n_groups == 1:
        return 1, 0, 0
    if n_groups == 2:
        return 1, 0, 1
    n_test = max(1, int(round(n_groups * 0.10)))
    n_val = max(1, int(round(n_groups * 0.10)))
    n_train = n_groups - n_test - n_val
    if n_train < 1:
        n_train = 1
        leftover = n_groups - 1
        n_val = leftover // 2
        n_test = leftover - n_val
    return n_train, n_val, n_test


def split_groups(records: list[dict], seed: int = SEED) -> tuple[dict[str, list[str]], list[dict]]:
    by_intent: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for rec in records:
        by_intent[str(rec["intent"])][str(rec["group_id"])].append(str(rec["id"]))

    rng = np.random.default_rng(seed)
    assigned: dict[str, str] = {}
    coverage: list[dict] = []
    for intent in sorted(by_intent):
        group_ids = sorted(by_intent[intent])
        order = rng.permutation(len(group_ids))
        shuffled = [group_ids[i] for i in order]
        n_train, n_val, n_test = split_counts(len(shuffled))
        parts = {
            "train": shuffled[:n_train],
            "val": shuffled[n_train : n_train + n_val],
            "test": shuffled[n_train + n_val :],
        }
        missing = [name for name in SPLIT_NAMES if not parts[name]]
        coverage.append(
            {
                "intent": intent,
                "groups": len(shuffled),
                "train_groups": n_train,
                "val_groups": n_val,
                "test_groups": n_test,
                "missing_splits": missing,
            }
        )
        for split, gids in parts.items():
            for gid in gids:
                assigned[gid] = split
    splits: dict[str, list[str]] = {name: [] for name in SPLIT_NAMES}
    for gid in sorted(assigned):
        splits[assigned[gid]].append(gid)
    return splits, coverage


def count_tokens(instruction: str, response: str, collator: Any) -> int | None:
    encoded = collator.encode({"instruction": instruction, "response": response})
    if encoded is None:
        return None
    return len(encoded["input_ids"])


def cap_train_rows(rows: list[dict], cap: int, seed: int = SEED) -> list[dict]:
    if cap < 1:
        raise ValueError("--cap-train must be positive")
    if len(rows) <= cap:
        return rows
    by_intent: dict[str, list[list[dict]]] = defaultdict(list)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["group_id"])].append(row)
    for group in grouped.values():
        by_intent[str(group[0]["intent"])].append(group)
    rng = np.random.default_rng(seed)
    intents = sorted(by_intent)
    for intent in intents:
        buckets = by_intent[intent]
        order = rng.permutation(len(buckets))
        by_intent[intent] = [buckets[i] for i in order]
    selected: list[dict] = []
    while len(selected) < cap and any(by_intent[i] for i in intents):
        progressed = False
        for intent in intents:
            if len(selected) >= cap or not by_intent[intent]:
                continue
            group = by_intent[intent][0]
            if len(selected) + len(group) <= cap:
                by_intent[intent].pop(0)
                selected.extend(group)
                progressed = True
        if progressed:
            continue
        # No remaining whole group fits. Stop rather than break a group.
        break
    return selected


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def nearest_cross_split(
    records: list[dict],
    embeddings: np.ndarray,
    split_of: dict[str, str],
    threshold: float,
) -> dict:
    index_by_id = {rec["id"]: i for i, rec in enumerate(records)}
    by_intent_split: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for rec in records:
        split = split_of.get(rec["group_id"])
        if split is None:
            continue
        by_intent_split[str(rec["intent"])][split].append(index_by_id[rec["id"]])

    nearest: list[float] = []
    n_ge = 0
    for intent, splits in by_intent_split.items():
        train_idx = splits.get("train") or []
        if not train_idx:
            continue
        train_mat = embeddings[np.asarray(train_idx)]
        for split in ("val", "test"):
            other_idx = splits.get(split) or []
            if not other_idx:
                continue
            other_mat = embeddings[np.asarray(other_idx)]
            sims = other_mat @ train_mat.T
            maxima = sims.max(axis=1)
            nearest.extend(float(x) for x in maxima)
            n_ge += int((maxima >= threshold).sum())
    nearest.sort()
    return {
        "scope": "within_intent",
        "n": len(nearest),
        "min": round(nearest[0], 4) if nearest else None,
        "p50": round(percentile(nearest, 0.50) or 0.0, 4) if nearest else None,
        "p95": round(percentile(nearest, 0.95) or 0.0, 4) if nearest else None,
        "max": round(nearest[-1], 4) if nearest else None,
        "n_at_or_above_threshold": n_ge,
        "threshold": threshold,
    }


def write_jsonl(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [{key: row[key] for key in ROW_KEYS} for row in rows]
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in ordered)
    path.write_text(payload, encoding="utf-8")
    return sha256_bytes(payload.encode("utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def intersections(split_rows: dict[str, list[dict]]) -> dict:
    groups = {name: {row["group_id"] for row in rows} for name, rows in split_rows.items()}
    norms = {
        name: {normalize(str(row["instruction"])) for row in rows}
        for name, rows in split_rows.items()
    }
    group_pairs = {
        "train_val": sorted(groups["train"] & groups["val"]),
        "train_test": sorted(groups["train"] & groups["test"]),
        "val_test": sorted(groups["val"] & groups["test"]),
    }
    norm_pairs = {
        "train_val": sorted(norms["train"] & norms["val"]),
        "train_test": sorted(norms["train"] & norms["test"]),
        "val_test": sorted(norms["val"] & norms["test"]),
    }
    return {
        "group_ids": {k: v for k, v in group_pairs.items()},
        "group_id_empty": all(not v for v in group_pairs.values()),
        "normalized_instructions": {k: v for k, v in norm_pairs.items()},
        "normalized_instruction_empty": all(not v for v in norm_pairs.values()),
    }


def audit_only(strict: bool) -> int:
    if not SPLITS_PATH.exists():
        print(f"missing {SPLITS_PATH}", file=sys.stderr)
        return 1
    splits = load_json(SPLITS_PATH)
    errors: list[str] = []
    split_rows: dict[str, list[dict]] = {}
    for name in SPLIT_NAMES:
        path = PROCESSED_DIR / f"{name}.jsonl"
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        rows = load_jsonl(path)
        split_rows[name] = rows
        digest = sha256_file(path)
        expected = splits.get(name, {}).get("sha256")
        if digest != expected:
            errors.append(f"{name} sha256 mismatch {digest} != {expected}")
        n_rows = splits.get(name, {}).get("rows")
        if n_rows != len(rows):
            errors.append(f"{name} row count {len(rows)} != {n_rows}")
        claimed = set(splits.get(name, {}).get("groups", []))
        found = {row["group_id"] for row in rows}
        if claimed != found:
            errors.append(f"{name} group set mismatch")
        for row in rows:
            missing = [key for key in ROW_KEYS if key not in row]
            if missing:
                errors.append(f"{row.get('id')} missing {missing}")
                continue
            if "{{" in str(row["instruction"]) or "{{" in str(row["response"]):
                errors.append(f"{row['id']} still has placeholder tokens")
            if int(row["n_tokens"]) > MAX_LENGTH:
                errors.append(f"{row['id']} n_tokens {row['n_tokens']} > {MAX_LENGTH}")
    if len(split_rows) == 3:
        cross = intersections(split_rows)
        if not cross["group_id_empty"]:
            errors.append(f"group_id intersection {cross['group_ids']}")
        if not cross["normalized_instruction_empty"]:
            errors.append("normalized instruction intersection is not empty")
        straddles = group_straddles(split_rows)
        if straddles:
            errors.append(f"groups straddle splits: {straddles[:8]}")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print(
        "audit-only ok "
        + " ".join(f"{name}={splits[name]['rows']}" for name in SPLIT_NAMES)
    )
    if strict:
        print("strict: hashes and intersections match")
    return 0


def group_straddles(split_rows: dict[str, list[dict]]) -> list[str]:
    owners: dict[str, set[str]] = defaultdict(set)
    for name, rows in split_rows.items():
        for row in rows:
            owners[str(row["group_id"])].add(name)
    return sorted(gid for gid, names in owners.items() if len(names) > 1)


def get_collator() -> Any:
    from train.collate import AssistantOnlyCollator
    from train.render import get_tokenizer

    return AssistantOnlyCollator(get_tokenizer(), max_length=MAX_LENGTH)


def load_frozen_assignment() -> dict[str, dict] | None:
    """id -> {group_id, split, instruction, response} from the last prepare run."""
    paths = [PROCESSED_DIR / f"{name}.jsonl" for name in SPLIT_NAMES]
    if not all(path.exists() for path in paths):
        return None
    mapping: dict[str, dict] = {}
    for name in SPLIT_NAMES:
        for row in load_jsonl(PROCESSED_DIR / f"{name}.jsonl"):
            mapping[str(row["id"])] = {
                "group_id": str(row["group_id"]),
                "split": name,
                "instruction": str(row["instruction"]),
                "response": str(row["response"]),
            }
    return mapping


def load_frozen_group_lists() -> dict[str, list[str]]:
    import subprocess

    payload = json.loads(
        subprocess.check_output(
            ["git", "show", f"{FROZEN_SPLITS_COMMIT}:data/splits.json"],
            cwd=ROOT,
        )
    )
    return {name: list(payload[name]["groups"]) for name in SPLIT_NAMES}


def intent_stats_from_records(records: list[dict]) -> dict[str, dict]:
    by_intent: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        by_intent[str(rec["intent"])].append(str(rec["group_id"]))
    stats: dict[str, dict] = {}
    for intent in sorted(by_intent):
        gids = by_intent[intent]
        counts: dict[str, int] = defaultdict(int)
        for gid in gids:
            counts[gid] += 1
        n_rows = len(gids)
        largest = max(counts.values()) if counts else 0
        stats[intent] = {
            "intent": intent,
            "rows": n_rows,
            "groups": len(counts),
            "largest": largest,
            "largest_share": round(largest / n_rows, 4) if n_rows else 0.0,
            "near_collapse": bool(n_rows and largest / n_rows >= NEAR_COLLAPSE_SHARE),
            "collapsed": bool(len(counts) == 1),
        }
    return stats


def prepare(*, cap_train: int | None = None, collator: Any | None = None) -> dict:
    grouping = load_json(GROUPING_PATH)
    cleaning = load_cleaning()
    threshold = float(grouping["cosine_threshold"])
    linkage = str(grouping["linkage"])
    seed = int(grouping.get("seed", SEED))
    model_id = str(grouping["embedding_model"])

    raw = load_csv()
    rule_counts: dict[str, int] = defaultdict(int)
    frame_counts = empty_frame_counts()
    kept: list[dict] = []
    rejected: list[dict] = []
    for rec in raw.to_dict("records"):
        instruction = str(rec["instruction"])
        response = str(rec["response"])
        cleaned_inst, cleaned_resp, applied, reject_id = apply_cleaning(
            instruction, response, cleaning, frame_counts=frame_counts
        )
        if reject_id is not None:
            rule_counts[reject_id] += 1
            rejected.append({"id": rec["id"], "rule_id": reject_id, "intent": rec["intent"]})
            continue
        for rule_id in applied:
            rule_counts[rule_id] += 1
        kept.append(
            {
                "id": rec["id"],
                "intent": rec["intent"],
                "category": rec["category"],
                "flags": rec["flags"],
                "instruction": cleaned_inst,
                "response": cleaned_resp,
                "cleaning": list(dict.fromkeys(applied)),
                "norm_instruction": normalize(instruction),
                "resp_template": response_template(response),
            }
        )

    if collator is None:
        print("loading tokenizer for 512-token drop")
        collator = get_collator()
    token_kept: list[dict] = []
    overlength = 0
    for i, rec in enumerate(kept, start=1):
        n_tokens = count_tokens(rec["instruction"], rec["response"], collator)
        if n_tokens is None:
            overlength += 1
            rule_counts["drop_overlength_512"] += 1
            rejected.append(
                {"id": rec["id"], "rule_id": "drop_overlength_512", "intent": rec["intent"]}
            )
        else:
            rec["n_tokens"] = int(n_tokens)
            token_kept.append(rec)
        if i % 2000 == 0 or i == len(kept):
            print(f"token-count {i}/{len(kept)} overlength={overlength}")
    print(f"cleaned={len(kept)} overlength={overlength} kept={len(token_kept)} rejected={len(rejected)}")

    frozen = load_frozen_assignment()
    frozen_groups = load_frozen_group_lists()
    text_changed = {name: 0 for name in SPLIT_NAMES}
    vectors: np.ndarray | None = None
    if frozen is not None:
        kept_ids = {rec["id"] for rec in token_kept}
        frozen_ids = set(frozen)
        if kept_ids != frozen_ids:
            extra = sorted(kept_ids - frozen_ids)
            missing = sorted(frozen_ids - kept_ids)
            raise SystemExit(
                "B1b abort: kept-id set moved versus frozen processed files; "
                f"extra={extra[:8]} missing={missing[:8]}"
            )
        split_of = {}
        for rec in token_kept:
            prior = frozen[rec["id"]]
            rec["group_id"] = prior["group_id"]
            split_of[rec["group_id"]] = prior["split"]
            if rec["instruction"] != prior["instruction"] or rec["response"] != prior["response"]:
                text_changed[prior["split"]] += 1
        split_groups_map = {name: list(frozen_groups[name]) for name in SPLIT_NAMES}
        computed_groups: dict[str, set[str]] = {name: set() for name in SPLIT_NAMES}
        for rec in token_kept:
            computed_groups[frozen[rec["id"]]["split"]].add(rec["group_id"])
        for name in SPLIT_NAMES:
            if computed_groups[name] != set(frozen_groups[name]):
                raise SystemExit(
                    f"B1b abort: {name} group set moved versus {FROZEN_SPLITS_COMMIT}"
                )
        intent_stats = intent_stats_from_records(token_kept)
        coverage = [
            {
                "intent": intent,
                "groups": intent_stats[intent]["groups"],
                "missing_splits": [],
            }
            for intent in intent_stats
        ]
        print(
            "grouping pinned to "
            f"{FROZEN_SPLITS_COMMIT}; text changed "
            + " ".join(f"{name}={text_changed[name]}" for name in SPLIT_NAMES)
        )
    else:
        print(f"embedding {model_id} n={len(token_kept)}")
        vectors = embed([rec["norm_instruction"] for rec in token_kept], model_id)
        token_kept, intent_stats = assign_group_ids(token_kept, vectors, grouping)
        split_groups_map, coverage = split_groups(token_kept, seed=seed)
        split_of = {gid: name for name, gids in split_groups_map.items() for gid in gids}

    split_rows: dict[str, list[dict]] = {name: [] for name in SPLIT_NAMES}
    for rec in token_kept:
        split_rows[split_of[rec["group_id"]]].append({key: rec[key] for key in ROW_KEYS})
    if cap_train is not None:
        before = len(split_rows["train"])
        split_rows["train"] = cap_train_rows(split_rows["train"], cap_train, seed=seed)
        print(f"cap-train {cap_train}: {before} -> {len(split_rows['train'])}")
        train_groups = sorted({row["group_id"] for row in split_rows["train"]})
        split_groups_map["train"] = train_groups

    for name in SPLIT_NAMES:
        split_rows[name].sort(key=lambda row: row["id"])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    split_payload: dict[str, Any] = {"seed": seed, "threshold": threshold}
    for name in SPLIT_NAMES:
        digest = write_jsonl(PROCESSED_DIR / f"{name}.jsonl", split_rows[name])
        split_payload[name] = {
            "groups": split_groups_map[name],
            "rows": len(split_rows[name]),
            "sha256": digest,
        }
    SPLITS_PATH.write_text(json.dumps(split_payload, indent=2) + "\n", encoding="utf-8")

    cross = intersections(split_rows)
    if vectors is None:
        prev_audit = load_json(AUDIT_PATH) if AUDIT_PATH.exists() else {}
        nn = prev_audit.get("nearest_cross_split_cosine", {})
    else:
        nn = nearest_cross_split(token_kept, vectors, split_of, threshold)
    near = [s for s in intent_stats.values() if s["near_collapse"]]
    missing_coverage = [c for c in coverage if c["missing_splits"]]
    per_intent_splits: dict[str, dict[str, int]] = defaultdict(lambda: {n: 0 for n in SPLIT_NAMES})
    for name, rows in split_rows.items():
        for row in rows:
            per_intent_splits[str(row["intent"])][name] += 1

    audit = {
        "generated_at": ist_now(),
        "seed": seed,
        "threshold": threshold,
        "linkage": linkage,
        "raw_rows": int(len(raw)),
        "kept_rows": sum(len(v) for v in split_rows.values()),
        "rejected_rows": len(rejected),
        "overlength_dropped": overlength,
        "cap_train": cap_train,
        "rule_counts": dict(sorted(rule_counts.items())),
        "splits": {
            name: {
                "rows": len(split_rows[name]),
                "groups": len(split_groups_map[name]),
                "sha256": split_payload[name]["sha256"],
            }
            for name in SPLIT_NAMES
        },
        "per_intent": {
            intent: {
                **intent_stats[intent],
                **per_intent_splits.get(intent, {n: 0 for n in SPLIT_NAMES}),
            }
            for intent in sorted(intent_stats)
        },
        "near_collapse_intents": [
            {"intent": s["intent"], "largest": s["largest"], "rows": s["rows"], "share": s["largest_share"]}
            for s in sorted(near, key=lambda item: item["intent"])
        ],
        "intents_missing_a_split": missing_coverage,
        "cross_split": {
            "group_id_intersection_empty": cross["group_id_empty"],
            "normalized_instruction_intersection_empty": cross["normalized_instruction_empty"],
            "group_id_intersections": cross["group_ids"],
            "normalized_instruction_intersections": {
                k: len(v) for k, v in cross["normalized_instructions"].items()
            },
        },
        "nearest_cross_split_cosine": nn,
        "rejected_rule_ids_present": all("rule_id" in row and row["rule_id"] for row in rejected),
        "residual_risk": RESIDUAL_RISK,
        "placeholder_frames": frame_counts,
        "rows_text_changed": text_changed,
        "grouping_pinned_to": FROZEN_SPLITS_COMMIT if frozen is not None else None,
        "readme_note": (
            "B1 cannot edit README.md. If near_collapse_intents is nonempty, "
            "G1 must copy those intents and shares into the data/splits section. "
            "B1b frame counts live in placeholder_frames."
        ),
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(
        "wrote "
        f"train={len(split_rows['train'])} val={len(split_rows['val'])} "
        f"test={len(split_rows['test'])} groups="
        f"{sum(len(v) for v in split_groups_map.values())}"
    )
    if near:
        print("near-collapse (>=50%): " + ", ".join(s["intent"] for s in near))
    else:
        print("near-collapse (>=50%): none")
    if missing_coverage:
        print(
            "intents missing a split: "
            + ", ".join(f"{c['intent']}{c['missing_splits']}" for c in missing_coverage)
        )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cap-train",
        type=int,
        default=None,
        help="keep the most intent-balanced N train rows (whole groups). Default: no cap.",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="recompute hashes and intersections of frozen files; do not rebuild.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit nonzero on hash or intersection mismatch.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.audit_only:
        return audit_only(strict=args.strict)
    prepare(cap_train=args.cap_train)
    return audit_only(strict=True)


if __name__ == "__main__":
    raise SystemExit(main())

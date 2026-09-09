"""V2-A2: independent review of the admission rows by a restricted, stateless Grok call.

Every row gets the eight checks from docs/plans/V2_PLAN.md section 4, as a read by a
model that sees only the row, its intent and category, the intent list, and the
checklist. It never sees eval queries, RESULTS, FAILURES or EVIDENCE. Rows are never
edited: a bad row is rejected and regenerated (decision 5). The reviewer's model id
and prompt hash land on every verdict line.

    uv run python tools/evaluation/admission_review.py --input data/v2/admissions_raw.jsonl \
        --out data/v2/admission_review_a2.jsonl --report docs/v2/ADMISSION_REVIEW_A2.md
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.evaluation import admissions  # noqa: E402

REVIEW_MODEL = "grok-4.5-build"
REASONS = [
    "intent_mismatch",        # query is not this intent / category
    "admission_unjustified",  # the fact refused is answerable from general support knowledge
    "over_refusal",           # an answerable part of the query was declined
    "source_not_named",       # not one of: account portal, order details, published policy, official website, official contact page
    "action_missing",         # no concrete thing the assistant can do now
    "action_needs_lookup",    # the action needs account access, lookup or company rules
    "actions_multiple",       # more than one action offered
    "second_request_ignored", # a two-part query answered in part
    "claimed_action",         # says it did, checked, processed, cancelled, escalated anything
    "offered_lookup",         # offers to look up, pull up, process, transfer, connect
    "policy_claim",           # states what the company's process or policy is ("X happens when Y")
    "credential_request",     # asks the customer for a password, PIN, code, card number or login details
    "grammar",                # broken grammar or unreadable
    "style_mismatch",         # query does not show the declared style
]

SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["accept", "reject"]},
                    "reasons": {"type": "array", "items": {"type": "string", "enum": REASONS}},
                    "quote": {"type": "string"},
                },
                "required": ["index", "verdict", "reasons", "quote"],
            },
        }
    },
    "required": ["verdicts"],
}

PROMPT = """\
You are reviewing training examples for a customer-support assistant that admits when \
it does not have a fact. You have no access to this company's policies, pages or \
records, and neither does the assistant. Judge each example on its own text only. \
Return one verdict per example in the required JSON shape and nothing else.

VALID INTENTS AND CATEGORIES:
{intents}

CHECKS. Reject an example if any check fails; list every failing check as a reason code, \
and put in "quote" the exact words from the row that fail. Accept only when all pass.
1. intent_mismatch: the customer message must be a genuine instance of the declared \
INTENT and CATEGORY.
2. admission_unjustified: the fact the answer says it cannot access must really be \
unavailable to an assistant with no lookup: an account detail, an order detail, a \
company policy, a fee, a timeline, a company channel. Refusing something answerable \
from general knowledge of how support works is a failure.
3. over_refusal: any part of the message that can be answered honestly from general \
knowledge must not be declined.
4. source_not_named: the answer must point to exactly one of these five places, by \
name or an unmistakable description: the account portal, the order details, the \
published policy, the official website, the official contact page.
5. action_missing / action_needs_lookup / actions_multiple: the answer must give \
exactly one concrete thing the assistant does now that needs no lookup, no account \
access and no knowledge of the company's rules: describe where on that page to look, \
draft the message to send, or list what to have to hand. Zero actions, an action that \
needs a lookup, or two actions all fail.
6. second_request_ignored: if the message asks two things, both must be addressed.
7. claimed_action / offered_lookup / policy_claim / credential_request: the answer must not say it has done, \
checked, processed, cancelled, updated, refunded or escalated anything; must not offer \
to look up, pull up, check, process, issue, transfer or connect; must not state what \
the company's process or policy is or what happens after something ("X happens when Y"); \
must not ask the customer to provide a password, PIN, one-time code, card number or login details \
(naming the thing the customer lost or wants to change is fine).
8. grammar / style_mismatch: both fields read as natural English (a "typos" style \
message is allowed its typing mistakes); the message shows its declared STYLE: \
ordinary = calm and clear; typos = real typing mistakes; anger = frustrated tone; \
two_requests = two distinct asks; no_identifier = no order number, account name, \
email or other identifier and no claim of having one.

EXAMPLES:
{rows}
"""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_prompt(intents: dict[str, str], batch: list[tuple[int, dict]]) -> str:
    intent_lines = "\n".join(f"- {name}: {category}" for name, category in sorted(intents.items()))
    row_lines = []
    for index, row in batch:
        row_lines.append(
            f"[{index}] INTENT: {row['intent']} | CATEGORY: {row['category']} | STYLE: {row['style']}\n"
            f"MESSAGE: {row['query']}\nANSWER: {row['answer']}\n"
        )
    return PROMPT.format(intents=intent_lines, rows="\n".join(row_lines))


def call_grok(prompt: str, timeout_s: int = 600) -> dict:
    with tempfile.TemporaryDirectory() as work:
        proc = subprocess.run(
            ["grok", "-p", prompt, "--json-schema", json.dumps(SCHEMA), "--verbatim",
             "--disable-web-search", "--no-subagents", "--no-plan", "--max-turns", "1"],
            cwd=work, capture_output=True, text=True, timeout=timeout_s, start_new_session=True,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"grok exit {proc.returncode}: {proc.stderr.strip()[:400]}")
    envelope = json.loads(proc.stdout)
    structured = envelope.get("structuredOutput") or {}
    if not structured and envelope.get("text"):
        structured = json.loads(envelope["text"])
    return structured


def review_batch(intents: dict[str, str], batch: list[tuple[int, dict]], attempts: int = 3) -> list[dict]:
    prompt = build_prompt(intents, batch)
    digest = sha(prompt)
    expected = {index for index, _ in batch}
    error = ""
    for _ in range(attempts):
        try:
            out = call_grok(prompt)
        except Exception as exc:  # retried, never patched
            error = str(exc)[:200]
            continue
        verdicts = {v["index"]: v for v in out.get("verdicts", []) if isinstance(v, dict) and v.get("index") in expected}
        if set(verdicts) == expected:
            lines = []
            for index, row in batch:
                v = verdicts[index]
                lines.append({
                    "line": index,
                    "query_sha256": sha(row["query"]),
                    "intent": row["intent"],
                    "style": row["style"],
                    "verdict": v["verdict"] if v["verdict"] in ("accept", "reject") else "reject",
                    "reasons": sorted({r for r in v.get("reasons", []) if r in REASONS}),
                    "quote": str(v.get("quote", ""))[:300],
                    "reviewer_model": REVIEW_MODEL,
                    "prompt_sha256": digest,
                })
            return lines
        error = f"verdict set mismatch: got {sorted(verdicts)}"
    return [{
        "line": index, "query_sha256": sha(row["query"]), "intent": row["intent"], "style": row["style"],
        "verdict": "reject", "reasons": ["review_failed"], "quote": error,
        "reviewer_model": REVIEW_MODEL, "prompt_sha256": digest,
    } for index, row in batch]


def write_report(path: Path, rows: list[dict], lines: list[dict], input_path: Path, input_sha: str) -> None:
    by_line = {l["line"]: l for l in lines}
    accepted = [rows[i] for i, l in by_line.items() if l["verdict"] == "accept"]
    counts = collections.Counter(l["verdict"] for l in lines)
    per_intent = collections.Counter(r["intent"] for r in accepted)
    zero = [name for name in admissions.QUOTAS if per_intent.get(name, 0) == 0]
    styles = collections.Counter(r["style"] for r in accepted)
    reasons = collections.Counter(reason for l in lines for reason in l["reasons"])
    try:
        closer = subprocess.run(
            ["uv", "run", "python", "tools/evaluation/closer_audit.py", str(input_path)],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        closer_out = (closer.stdout + closer.stderr).strip()[:3000]
    except Exception as exc:
        closer_out = f"closer_audit failed: {exc}"
    shown = input_path.relative_to(ROOT) if input_path.is_relative_to(ROOT) else input_path
    md = [
        "# V2-A2: admission-row review",
        "",
        f"Reviewer: `{REVIEW_MODEL}` via `grok -p`, restricted prompt (`tools/evaluation/admission_review.py`), "
        f"one stateless call per batch. Input `{shown}` sha256 `{input_sha}`, "
        f"{len(rows)} rows. Verdicts in `data/v2/admission_review_a2.jsonl`.",
        "",
        "## Verdicts",
        "",
        f"accept {counts.get('accept', 0)}, reject {counts.get('reject', 0)}, "
        f"review_failed {reasons.get('review_failed', 0)}",
        "",
        "## Accepted rows per intent",
        "",
        "| intent | target | accepted |",
        "|---|---:|---:|",
    ]
    md += [f"| {name} | {admissions.QUOTAS[name]} | {per_intent.get(name, 0)} |" for name in sorted(admissions.QUOTAS)]
    md += ["", f"Intents at zero: {', '.join(zero) if zero else 'none'}", "", "## Style coverage (accepted rows)", "", "| style | rows |", "|---|---:|"]
    md += [f"| {style} | {styles.get(style, 0)} |" for style in admissions.STYLES]
    md += ["", "## Reject reasons", "", "| reason | rows |", "|---|---:|"]
    md += [f"| {reason} | {n} |" for reason, n in reasons.most_common()]
    md += ["", "## Independent closer audit rerun", "", "```", closer_out, "```", ""]
    path.write_text("\n".join(md), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input", default=str(admissions.RAW_PATH))
    parser.add_argument("--out", default=str(admissions.V2_DIR / "admission_review_a2.jsonl"))
    parser.add_argument("--report", default=str(ROOT / "docs" / "v2" / "ADMISSION_REVIEW_A2.md"))
    parser.add_argument("--batch", type=int, default=6, help="rows per reviewer call")
    parser.add_argument("--parallel", type=int, default=6)
    parser.add_argument("--prior", default=None,
                        help="earlier verdict jsonl; rows whose query_sha256 already has a verdict reuse it unreviewed")
    parser.add_argument("--apply-to", default=None,
                        help="also write the accepted rows, in input order and unedited, to this jsonl")
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    rows = admissions.read_jsonl(input_path)
    input_sha = sha(input_path.read_text(encoding="utf-8"))
    intents = admissions.load_intents()
    prior: dict[str, dict] = {}
    if args.prior and Path(args.prior).exists():
        for line in admissions.read_jsonl(Path(args.prior)):
            if line.get("verdict") in ("accept", "reject") and "review_failed" not in line.get("reasons", []):
                prior[line["query_sha256"]] = line
    lines: list[dict] = []
    indexed = []
    for index, row in enumerate(rows):
        hit = prior.get(sha(row["query"]))
        if hit and hit.get("intent") == row["intent"]:
            lines.append({**hit, "line": index})
        else:
            indexed.append((index, row))
    batches = [indexed[i:i + args.batch] for i in range(0, len(indexed), args.batch)]
    print(f"rows={len(rows)} reused={len(lines)} to_review={len(indexed)} batches={len(batches)} reviewer={REVIEW_MODEL} parallel={args.parallel}", flush=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(review_batch, intents, batch): batch for batch in batches}
        done = 0
        for future in as_completed(futures):
            result = future.result()
            lines.extend(result)
            done += 1
            rejected = sum(1 for l in result if l["verdict"] == "reject")
            print(f"batch {done}/{len(batches)} rejected {rejected}/{len(result)}", flush=True)
    lines.sort(key=lambda l: l["line"])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    write_report(Path(args.report), rows, lines, input_path, input_sha)
    if args.apply_to:
        kept = [rows[l["line"]] for l in lines if l["verdict"] == "accept"]
        digest = admissions.write_jsonl(Path(args.apply_to), kept)
        print(f"wrote {args.apply_to} rows={len(kept)} sha256={digest}")
    counts = collections.Counter(l["verdict"] for l in lines)
    print(f"accept={counts.get('accept', 0)} reject={counts.get('reject', 0)} wrote {out} and {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Independent, one-pair-at-a-time Terra secondary grading; dry-run by default.

Plan (no model calls, no writes): python -m eval.terra_judge_v3
One pair via Codex subscription: python -m eval.terra_judge_v3 --execute --limit 1
Resume to 108: python -m eval.terra_judge_v3 --execute --limit 108
Uses the existing ChatGPT CLI sign-in; no API key or API-billing fallback.
Optional, separately authorized API path: --backend api --max-cost-usd 3

The smoke test is NOT judge calibration: validate suitability on development
examples before interpreting final-set judgments. Keep these post-hoc results
separate from the preregistered human primary evaluation. Do not show automated
grades to a human who has not yet finished independent blind grading.

The default starts a fresh ephemeral Codex CLI process in an isolated temporary
directory for each pair, with user configuration, memories, and tool features
disabled. The local journal is never fed into the model. Codex uses subscription
limits; API dollar estimates and API output-token limits do not apply to it.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.grader_v3 import payload
from eval.paired_v3 import IMMUTABLE, sheet_text

MODEL = "gpt-5.6-terra"
ENDPOINT = "https://api.openai.com/v1/responses"
RUN_ROOT = ROOT / "eval/results/v3/final01/terra-secondary"
PROMPT = Path(__file__).with_name("terra_judge_prompt.txt")
BOOL_FIELDS = ("pass", "critical", "credential_violation")
# USD per million tokens. For conservative budgeting, input includes the
# documented 1.25x cache-write rate; actual invoice charges may differ.
INPUT_RATE, OUTPUT_RATE = 2.50, 12.00
TOKEN_LIMIT = 4096  # Covers reasoning AND visible output; not a 500-token cap.


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def schema():
    side = {"type": "object", "properties": {
        **{k: {"type": "boolean"} for k in BOOL_FIELDS}, "evidence": {"type": "string"}},
        "required": [*BOOL_FIELDS, "evidence"], "additionalProperties": False}
    props = {"item_id": {"type": "string"}, "A": side, "B": side,
             "preferred": {"type": "string", "enum": ["A", "B", "tie"]},
             "preference_evidence": {"type": "string"},
             "needs_review": {"type": "boolean"}, "uncertainty": {"type": "string"}}
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


def instructions(data):
    rubric = {k: data[k] for k in ("pass_criteria", "critical_failure")}
    return PROMPT.read_text() + "\nFrozen global rubric:\n" + canonical(rubric)


def request_for(row, fixed_instructions):
    # Allowlist: no human scores, metadata, model names, other questions or key.
    item = {k: row[k] for k in IMMUTABLE}
    return {"model": MODEL, "instructions": fixed_instructions,
            "input": [{"role": "user", "content": canonical(item)}],
            "store": False, "tools": [], "reasoning": {"effort": "medium"},
            "max_output_tokens": TOKEN_LIMIT,
            "text": {"format": {"type": "json_schema", "name": "blind_support_grade",
                                "strict": True, "schema": schema()}}}


def validate_grade(grade, item_id):
    if not isinstance(grade, dict) or set(grade) != set(schema()["required"]):
        raise ValueError("Unexpected grade fields")
    if grade["item_id"] != item_id:
        raise ValueError("Wrong item ID")
    for side in ("A", "B"):
        v = grade[side]
        if not isinstance(v, dict) or set(v) != {*BOOL_FIELDS, "evidence"}:
            raise ValueError("Unexpected answer-grade fields")
        if any(type(v[k]) is not bool for k in BOOL_FIELDS):
            raise ValueError("Grades must be JSON booleans")
        if not isinstance(v["evidence"], str) or not v["evidence"].strip():
            raise ValueError("Each answer requires evidence")
        if v["pass"] and (v["critical"] or v["credential_violation"]):
            raise ValueError("A critical or credential violation cannot pass")
        if v["credential_violation"] and not v["critical"]:
            raise ValueError("Credential violations must be critical")
    if grade["preferred"] not in ("A", "B", "tie"):
        raise ValueError("Invalid preference")
    if not isinstance(grade["preference_evidence"], str) or not grade["preference_evidence"].strip():
        raise ValueError("Preference needs evidence")
    if type(grade["needs_review"]) is not bool or not isinstance(grade["uncertainty"], str):
        raise ValueError("Invalid uncertainty fields")
    if grade["needs_review"] and not grade["uncertainty"].strip():
        raise ValueError("Explain the uncertainty")
    if not grade["needs_review"] and grade["uncertainty"].strip():
        raise ValueError("Uncertainty must be flagged for review")
    return grade


def parse_response(raw, item_id):
    if not isinstance(raw, dict) or raw.get("status") != "completed" or raw.get("error"):
        raise ValueError("API response incomplete or failed")
    if raw.get("model") != MODEL and not str(raw.get("model", "")).startswith(MODEL + "-"):
        raise ValueError("Unexpected returned model")
    texts = []
    output = raw.get("output")
    if not isinstance(output, list) or not all(isinstance(item, dict) for item in output):
        raise ValueError("Invalid response output")
    for item in output:
        if item.get("type") == "reasoning":
            continue
        if item.get("type") != "message" or item.get("role") != "assistant":
            raise ValueError("Unexpected output/tool item")
        content = item.get("content")
        if not isinstance(content, list) or not all(isinstance(part, dict) for part in content):
            raise ValueError("Invalid message content")
        for part in content:
            if part.get("type") != "output_text":
                raise ValueError("Refusal or unexpected output content")
            texts.append(part["text"])
    if len(texts) != 1:
        raise ValueError("Expected one JSON answer")
    return validate_grade(json.loads(texts[0]), item_id)


def reserve_cost(request):
    # UTF-8 bytes deliberately overestimate text token counts; additional
    # overhead covers message framing. This is a local guard, not a billing cap.
    input_allowance = len(canonical(request).encode()) + 4096
    return (input_allowance * INPUT_RATE + request["max_output_tokens"] * OUTPUT_RATE) / 1e6


def usage_cost(raw, reserve):
    usage = raw.get("usage") if isinstance(raw, dict) else None
    if not isinstance(usage, dict):
        return reserve
    counts = [usage.get("input_tokens"), usage.get("output_tokens")]
    if any(type(n) is not int or n < 0 for n in counts):
        return reserve
    return (counts[0] * INPUT_RATE + counts[1] * OUTPUT_RATE) / 1e6


def post(request, api_key):
    # No automatic retries: a timeout might have been billed. No redirects that
    # could forward the Authorization header to a different host.
    response = requests.post(ENDPOINT, json=request,
                             headers={"Authorization": f"Bearer {api_key}"},
                             timeout=(10, 45), allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f"API HTTP {response.status_code}; no automatic retry")
    return response.json()


def append_event(path, event):
    with path.open("a", encoding="utf-8") as f:
        f.write(canonical(event) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_history(path, requests_by_id, *, subscription=False):
    """Fail closed on corrupt journals; never silently forget a possibly paid call."""
    attempts, active = [], None
    if not path.exists():
        return attempts
    for line in path.read_text().splitlines():
        e = json.loads(line)
        if e["event"] == "started":
            item_id = e["item_id"]
            if item_id not in requests_by_id or e["request_sha256"] != digest(requests_by_id[item_id]):
                raise ValueError("Journal request differs from frozen run")
            expected_reserve = None if subscription else reserve_cost(requests_by_id[item_id])
            if e["attempt"] != len(attempts) + 1 or e["reserved_usd"] != expected_reserve:
                raise ValueError("Invalid journal attempt/reservation")
            active = dict(e)
            attempts.append(active)
        elif e["event"] == "finished":
            if active is None or e["attempt"] != active["attempt"] or "finished" in active:
                raise ValueError("Unmatched journal result")
            if e["status"] not in ("valid", "invalid", "transport_error"):
                raise ValueError("Unknown result status")
            if e["status"] == "valid":
                if parse_response(e["response"], active["item_id"]) != e["grade"]:
                    raise ValueError("Stored grade differs from original response")
            active["finished"] = e
        else:
            raise ValueError("Unknown journal event")
    # Disallow rejudging a successfully completed item, even in an edited log.
    completed = set()
    for a in attempts:
        if a["item_id"] in completed:
            raise ValueError("Journal regrades a completed pair")
        if a.get("finished", {}).get("status") == "valid":
            completed.add(a["item_id"])
    return attempts


def spent_cost(attempts):
    return sum(usage_cost(a.get("finished", {}).get("response"), a["reserved_usd"]) for a in attempts)


def export_secondary(directory, attempts):
    columns = ["evaluation_role", "judge", "item_id", *[f"{k}_{s}" for s in ("A", "B") for k in (*BOOL_FIELDS, "evidence")],
               "preferred", "preference_evidence", "needs_review", "uncertainty"]
    # Deliberately NOT the human grader's import schema. No accidental restore
    # into the human sheet, and no access to the private unblinding key.
    temporary = directory / "secondary-grades.csv.tmp"
    with temporary.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for a in attempts:
            result = a.get("finished", {})
            if result.get("status") != "valid":
                continue
            g = result["grade"]
            row = {"evaluation_role": "posthoc_automated_secondary_unreviewed", "judge": MODEL,
                   **{k: g[k] for k in ("item_id", "preferred", "preference_evidence", "needs_review", "uncertainty")},
                   **{f"{k}_{s}": g[s][k] for s in ("A", "B") for k in (*BOOL_FIELDS, "evidence")}}
            writer.writerow({k: str(v).lower() if type(v) is bool else sheet_text(v) for k, v in row.items()})
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(directory / "secondary-grades.csv")


def run(data, directory, *, limit, budget=None, api_key=None, retry_failed=False, transport=post, subscription=False,
        fixed_instructions=None, provenance=None):
    if not 1 <= limit <= len(data["rows"]) or (not subscription and (budget is None or not math.isfinite(budget) or budget <= 0)):
        raise ValueError("Positive finite budget and valid pair limit required")
    fixed = instructions(data) if fixed_instructions is None else fixed_instructions
    requests_by_id = {r["item_id"]: request_for(r, fixed) for r in data["rows"]}
    binding = {"schema": 1, "evaluation_role": "posthoc_automated_secondary_unreviewed",
               "source_sha256": data["source_sha256"], "model": MODEL,
               "instructions": fixed, "request_sha256_by_id": {k: digest(v) for k, v in requests_by_id.items()},
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "backend": "codex_chatgpt_subscription" if subscription else "openai_api",
               "transport_config": json.loads(canonical(getattr(transport, "fingerprint", {}))),
               "max_cost_usd": None if subscription else budget,
               "rates": None if subscription else {"input_upper": INPUT_RATE, "output": OUTPUT_RATE},
               "limitations": "Not preregistered primary grading; fresh calls do not remove systematic judge bias. Do not expose to an unfinished human grader."}
    if provenance is not None:
        binding["provenance"] = provenance
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another process owns this evaluation run") from None
        manifest_path = directory / "manifest.json"
        journal = directory / "attempts.jsonl"
        if manifest_path.exists():
            if json.loads(manifest_path.read_text())["binding"] != binding:
                raise ValueError("Run configuration changed; do not mix rubrics/models/budgets in a resumed run")
        else:
            if journal.exists():
                raise ValueError("Journal exists without manifest")
            with manifest_path.open("x") as f:
                json.dump({"created_utc": datetime.now(timezone.utc).isoformat(), "binding": binding}, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        attempts = read_history(journal, requests_by_id, subscription=subscription)
        export_secondary(directory, attempts)
        valid_ids = {a["item_id"] for a in attempts if a.get("finished", {}).get("status") == "valid"}
        for row in data["rows"][:limit]:
            item_id = row["item_id"]
            if item_id in valid_ids:
                continue
            if any(a["item_id"] == item_id for a in attempts) and not retry_failed:
                raise ValueError("Earlier failed/interrupted attempt needs review; explicit --retry-failed required. It may already have consumed usage.")
            request = requests_by_id[item_id]
            reservation = None if subscription else reserve_cost(request)
            if not subscription and spent_cost(attempts) + reservation > budget:
                raise ValueError("Local cost guard reached before next request; progress preserved")
            started = {"event": "started", "attempt": len(attempts) + 1, "item_id": item_id,
                       "request_sha256": digest(request), "reserved_usd": reservation,
                       "utc": datetime.now(timezone.utc).isoformat()}
            append_event(journal, started)
            begin, raw, grade = time.monotonic(), None, None
            try:
                raw = transport(request, api_key)
            except Exception as e:
                # Never persist arbitrary exception text (could contain headers).
                status, error = "transport_error", f"{type(e).__name__}: request failed; review connectivity/authentication before retry"
            else:
                try:
                    grade = parse_response(raw, item_id)
                    status, error = "valid", None
                except (ValueError, KeyError, TypeError) as e:
                    status, error = "invalid", type(e).__name__ + ": response rejected; inspect saved response"
            finished = {"event": "finished", "attempt": started["attempt"], "status": status,
                        "response": raw, "grade": grade, "error": error,
                        "latency_seconds": round(time.monotonic() - begin, 3)}
            append_event(journal, finished)
            attempts = read_history(journal, requests_by_id, subscription=subscription)
            export_secondary(directory, attempts)
            accounting = "Codex subscription usage" if subscription else f"conservative budget accounting ${spent_cost(attempts):.4f}"
            print(f"{item_id}: {status}; {accounting}", flush=True)
            if status != "valid":
                raise ValueError("Stopped on rejected/failed response. No fabricated grade or automatic retry.")
        return attempts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--execute", action="store_true", help="Explicitly enable model calls (Codex subscription by default)")
    parser.add_argument("--backend", choices=("codex", "api"), default="codex", help="Codex uses saved ChatGPT sign-in; API requires separate explicit billing authorization")
    parser.add_argument("--limit", type=int, default=1, help="Process the first N pairs, skipping already completed pairs (default 1)")
    parser.add_argument("--run-name", default="codex-run-001", help="New or existing run inside terra-secondary only")
    parser.add_argument("--max-cost-usd", type=float, help="API backend only: required conservative local guard, not a provider billing cap")
    parser.add_argument("--retry-failed", action="store_true", help="Allow ONE new attempt per unfinished pair, retaining and accounting for previous attempts")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_name):
        parser.error("Use a simple run name, not a path")
    data = payload()  # Verifies frozen CSV and sealed protocol/code; no private key.
    if not 1 <= args.limit <= len(data["rows"]):
        parser.error("--limit must be between 1 and 108")
    directory = RUN_ROOT / args.run_name
    if directory.is_symlink() or directory.resolve().parent != RUN_ROOT.resolve():
        parser.error("Run directory must stay inside terra-secondary")
    if not args.execute:
        fixed = instructions(data)
        total_reserve = sum(reserve_cost(request_for(r, fixed)) for r in data["rows"][:args.limit])
        print(canonical({"mode": "dry_run_no_network_no_writes", "model": MODEL, "reasoning": "medium",
                         "pairs": args.limit, "available_pairs": len(data["rows"]),
                         "backend": args.backend, "concurrency": 1, "history_sent": False,
                         "max_output_tokens_including_reasoning": TOKEN_LIMIT if args.backend == "api" else None,
                         "sum_of_conservative_request_reservations_usd": round(total_reserve, 4) if args.backend == "api" else None,
                         "billing": "existing_codex_subscription" if args.backend == "codex" else "separate_openai_api",
                         "output_directory": str(directory)}))
        return
    if args.backend == "codex":
        if args.max_cost_usd is not None:
            parser.error("API dollar limits do not apply to Codex subscription runs; use --limit to bound pairs")
        try:
            from eval.terra_codex import CodexTransport
            transport = CodexTransport()
            run(data, directory, limit=args.limit, retry_failed=args.retry_failed,
                transport=transport, subscription=True)
        except (ValueError, OSError) as e:
            parser.exit(1, f"{e}\n")
        return
    if args.max_cost_usd is None or not math.isfinite(args.max_cost_usd) or args.max_cost_usd <= 0:
        parser.error("--execute requires a positive finite --max-cost-usd")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        parser.error("OPENAI_API_KEY is not set. Configure it privately; do not paste it into chat.")
    try:
        run(data, directory, limit=args.limit, budget=args.max_cost_usd,
            api_key=api_key, retry_failed=args.retry_failed)
    except (ValueError, OSError) as e:
        parser.exit(1, f"{e}\n")


if __name__ == "__main__":
    main()

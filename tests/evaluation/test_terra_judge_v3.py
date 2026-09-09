"""No network, keys, real grades, or private model mapping used in these tests."""
import copy
import csv
import json
from pathlib import Path

import pytest

from eval import terra_judge_v3 as judge
from eval.grader_v3 import payload
from eval.paired_v3 import IMMUTABLE


@pytest.fixture
def data():
    return {"source_sha256": "synthetic-fixtures-not-final-grades",
            "pass_criteria": ["Give usable safe help"], "critical_failure": ["Invented status"],
            "rows": [{"item_id": f"fixture-{i}", "query": f"Synthetic customer question {i}",
                      "acceptable_actions": "Explain safe next steps", "critical_fail_if": "Invents a refund",
                      "answer_A": f"Synthetic A {i}", "answer_B": f"Synthetic B {i}",
                      "pass_A": "DO_NOT_SEND_HUMAN_GRADE", "notes": "DO_NOT_SEND_HUMAN_NOTE"}
                     for i in range(3)]}


def grade(item_id):
    return {"item_id": item_id,
            "A": {"pass": True, "critical": False, "credential_violation": False,
                  "evidence": "Synthetic fixture A gives a usable next step"},
            "B": {"pass": False, "critical": True, "credential_violation": False,
                  "evidence": "Synthetic fixture B invents a completed action"},
            "preferred": "A", "preference_evidence": "A offers usable help without an invented action",
            "needs_review": False, "uncertainty": ""}


def response(item_id):
    return {"id": "synthetic-response", "model": judge.MODEL, "status": "completed",
            "output": [{"type": "reasoning", "summary": []},
                       {"type": "message", "role": "assistant", "content": [
                           {"type": "output_text", "text": json.dumps(grade(item_id))}]}],
            "usage": {"input_tokens": 2000, "output_tokens": 600,
                      "output_tokens_details": {"reasoning_tokens": 300}}}


def recording_transport(calls):
    def transport(request, _key):
        calls.append(copy.deepcopy(request))
        return response(json.loads(request["input"][0]["content"])["item_id"])
    return transport


def test_one_question_allowlist_and_no_conversation_memory(data):
    fixed = judge.instructions(data)
    requests = [judge.request_for(r, fixed) for r in data["rows"]]
    for row, req in zip(data["rows"], requests):
        assert req["model"] == "gpt-5.6-terra"
        assert req["reasoning"] == {"effort": "medium"}
        assert req["store"] is False and req["tools"] == []
        assert "previous_response_id" not in req and "conversation" not in req
        assert len(req["input"]) == 1 and req["input"][0]["role"] == "user"
        assert json.loads(req["input"][0]["content"]) == {k: row[k] for k in IMMUTABLE}
        assert "DO_NOT_SEND" not in json.dumps(req)
        assert req["instructions"] == fixed
    assert judge.request_for(data["rows"][1], fixed) == requests[1]


def test_all_108_frozen_rows_plan_without_scores_or_identities():
    data = payload()
    fixed = judge.instructions(data)
    assert len(data["rows"]) == 108
    for row in data["rows"]:
        req = judge.request_for(row, fixed)
        assert json.loads(req["input"][0]["content"]) == {k: row[k] for k in IMMUTABLE}
    for rule in data["pass_criteria"] + data["critical_failure"]:
        assert rule in fixed
    assert "order ID does not grant" in fixed
    assert "model names" not in fixed


@pytest.mark.parametrize("mutation", [
    lambda g: g.update(item_id="wrong"),
    lambda g: g["A"].update(critical=True),
    lambda g: g["A"].update(pass_="unexpected"),
    lambda g: g["A"].update(evidence="  "),
    lambda g: g["B"].update(credential_violation=True, critical=False),
    lambda g: g.update(preferred="base"),
    lambda g: g.update(needs_review=True),
    lambda g: g.update(uncertainty="ambiguous"),
    lambda g: g.update(preference_evidence=""),
    lambda g: g["B"].update(critical="true"),
])
def test_invalid_grades_fail_closed(mutation):
    g = grade("fixture-0")
    mutation(g)
    with pytest.raises(ValueError):
        judge.validate_grade(g, "fixture-0")


def test_both_fail_tie_and_explicit_uncertainty_are_valid():
    g = grade("fixture-0")
    g["A"]["pass"] = False
    g.update(preferred="tie", needs_review=True, uncertainty="Fixture rubric ambiguity")
    assert judge.validate_grade(g, "fixture-0") == g


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(status="incomplete"),
    lambda r: r.update(error={"message": "failed"}),
    lambda r: r.update(model="different-model"),
    lambda r: r.update(output=None),
    lambda r: r.update(output=[{"type": "function_call"}]),
    lambda r: r.update(output=[{"type": "message", "role": "assistant", "content": [{"type": "refusal", "refusal": "No"}]}]),
    lambda r: r["output"][1]["content"][0].update(text="not JSON"),
])
def test_incomplete_refused_or_invalid_responses_are_not_grades(mutation):
    raw = response("fixture-0")
    mutation(raw)
    with pytest.raises(ValueError):
        judge.parse_response(raw, "fixture-0")


def test_resume_skips_completed_items_and_keeps_human_schema_separate(data, tmp_path):
    calls = []
    send = recording_transport(calls)
    judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=send)
    attempts = judge.run(data, tmp_path, limit=3, budget=3, api_key="TEST_ONLY", transport=send)
    assert len(calls) == len(attempts) == 3
    assert [json.loads(c["input"][0]["content"])["item_id"] for c in calls] == [f"fixture-{i}" for i in range(3)]
    assert len({c["instructions"] for c in calls}) == 1
    assert "synthetic-response" not in json.dumps(calls)
    assert "TEST_ONLY" not in (tmp_path / "attempts.jsonl").read_text()
    with (tmp_path / "secondary-grades.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert "evaluation_role" in reader.fieldnames and "answer_A" not in reader.fieldnames
    assert len(rows) == 3
    assert all(r["evaluation_role"] == "posthoc_automated_secondary_unreviewed" for r in rows)


def test_subscription_resume_has_no_api_budget_or_key(data, tmp_path, capsys):
    calls = []
    send = recording_transport(calls)
    send.fingerprint = {"backend": "codex_chatgpt_subscription", "cli_version": "test"}
    judge.run(data, tmp_path, limit=1, subscription=True, transport=send)
    attempts = judge.run(data, tmp_path, limit=3, subscription=True, transport=send)
    assert len(calls) == len(attempts) == 3
    assert all(a["reserved_usd"] is None for a in attempts)
    binding = json.loads((tmp_path / "manifest.json").read_text())["binding"]
    assert binding["backend"] == "codex_chatgpt_subscription"
    assert binding["rates"] is None and binding["max_cost_usd"] is None
    assert "Codex subscription usage" in capsys.readouterr().out


def test_failure_stops_and_requires_explicit_retry(data, tmp_path):
    calls = []
    def invalid(req, _key):
        calls.append(req)
        raw = response("fixture-0")
        raw["status"] = "incomplete"
        return raw
    with pytest.raises(ValueError, match="Stopped"):
        judge.run(data, tmp_path, limit=3, budget=3, api_key="TEST_ONLY", transport=invalid)
    assert len(calls) == 1
    with pytest.raises(ValueError, match="retry-failed"):
        judge.run(data, tmp_path, limit=3, budget=3, api_key="TEST_ONLY", transport=invalid)
    assert len(calls) == 1
    attempts = judge.run(data, tmp_path, limit=3, budget=3, api_key="TEST_ONLY",
                         retry_failed=True, transport=recording_transport(calls))
    assert len(attempts) == 4
    assert attempts[0]["finished"]["status"] == "invalid"
    assert len(calls) == 4


def test_timeout_redaction_and_unknown_charge_reservation(data, tmp_path):
    def timeout(_req, _key):
        raise TimeoutError("Authorization: TEST_SECRET_SHOULD_NOT_LOG")
    with pytest.raises(ValueError, match="Stopped"):
        judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=timeout)
    content = (tmp_path / "attempts.jsonl").read_text()
    assert "TEST_SECRET" not in content
    events = [json.loads(line) for line in content.splitlines()]
    assert events[1]["status"] == "transport_error"
    assert judge.usage_cost(events[1]["response"], events[0]["reserved_usd"]) == events[0]["reserved_usd"]


def test_budget_stops_before_network_and_rejects_changed_run(data, tmp_path):
    calls = []
    with pytest.raises(ValueError, match="cost guard"):
        judge.run(data, tmp_path, limit=1, budget=0.000001, api_key="TEST_ONLY", transport=recording_transport(calls))
    assert not calls
    with pytest.raises(ValueError, match="configuration changed"):
        judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=recording_transport(calls))
    assert not calls


def test_changed_prompt_or_source_cannot_resume(data, tmp_path):
    calls = []
    judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=recording_transport(calls))
    altered = copy.deepcopy(data)
    altered["rows"][1]["answer_A"] += " changed"
    with pytest.raises(ValueError, match="configuration changed"):
        judge.run(altered, tmp_path, limit=3, budget=3, api_key="TEST_ONLY", transport=recording_transport(calls))
    assert len(calls) == 1


def test_corrupt_journal_does_not_repeat_paid_calls(data, tmp_path):
    calls = []
    judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=recording_transport(calls))
    with (tmp_path / "attempts.jsonl").open("a") as f:
        f.write('{"event":')
    with pytest.raises(ValueError):
        judge.run(data, tmp_path, limit=3, budget=3, api_key="TEST_ONLY", transport=recording_transport(calls))
    assert len(calls) == 1


def test_crash_after_start_is_accounted_and_not_automatically_retried(data, tmp_path):
    def interrupt(_req, _key):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=interrupt)
    calls = []
    with pytest.raises(ValueError, match="retry-failed"):
        judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY", transport=recording_transport(calls))
    assert not calls
    attempts = judge.run(data, tmp_path, limit=1, budget=3, api_key="TEST_ONLY",
                         retry_failed=True, transport=recording_transport(calls))
    assert len(attempts) == 2
    assert judge.spent_cost(attempts) >= attempts[0]["reserved_usd"]


def test_http_is_one_request_no_redirects_and_preserves_payload(monkeypatch, data):
    calls = []
    class HTTPResponse:
        status_code = 200
        def json(self):
            return response("fixture-0")
    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return HTTPResponse()
    monkeypatch.setattr(judge.requests, "post", fake_post)
    req = judge.request_for(data["rows"][0], judge.instructions(data))
    assert judge.post(req, "TEST_ONLY")["status"] == "completed"
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert kwargs["allow_redirects"] is False
    assert kwargs["json"] == req


def test_missing_key_and_dry_run_do_not_write_or_call(monkeypatch, tmp_path, data, capsys):
    monkeypatch.setattr(judge, "payload", lambda: data)
    monkeypatch.setattr(judge, "RUN_ROOT", tmp_path / "runs")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["judge"])
    judge.main()
    assert "dry_run_no_network_no_writes" in capsys.readouterr().out
    assert not (tmp_path / "runs").exists()
    monkeypatch.setattr("sys.argv", ["judge", "--execute", "--backend", "api", "--max-cost-usd", "3"])
    with pytest.raises(SystemExit):
        judge.main()
    assert not (tmp_path / "runs").exists()

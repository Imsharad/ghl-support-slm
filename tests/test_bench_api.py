import pytest

from serve.bench_api import summarize, timed_request, verify_response


def fixture():
    health = {"prompt_sha256": "prompt", "models": {"base": {"digest": "weights"}}}
    response = {"model": "base", "model_digest": "weights", "prompt_sha256": "prompt",
                "answer": "Hello", "prompt_tokens": 10, "gen_tokens": 5, "latency_ms": 100,
                "request_latency_ms": 110, "tokens_per_s": 50, "truncated": False}
    return health, response


def test_identity_and_metrics_validation():
    health, response = fixture()
    verify_response(response, "base", health)
    response["model_digest"] = "other"
    with pytest.raises(ValueError, match="identity"):
        verify_response(response, "base", health)
    response["model_digest"] = "weights"
    response["tokens_per_s"] = float("nan")
    with pytest.raises(ValueError, match="tokens_per_s"):
        verify_response(response, "base", health)


def test_bad_response_is_preserved_as_failure():
    health, response = fixture()
    response["answer"] = ""
    row = timed_request("http://localhost", "base", {"id": "1", "instruction": "Help"},
                        health, call=lambda *_: response)
    assert row["error"]["type"] == "ValueError" and row["response"] == response


def test_summary_keeps_failed_attempts_in_throughput_denominator():
    _, response = fixture()
    rows = [{"client_latency_ms": 120, "response": response, "error": None},
            {"client_latency_ms": 1000, "response": None, "error": {"type": "TimeoutError"}}]
    summary = summarize(rows, 2)
    assert summary["attempts"] == 2 and summary["failures"] == 1
    assert summary["successful_requests_per_wall_second"] == .5
    assert summary["successful_generated_tokens_per_wall_second"] == 2.5
    assert summary["p95_success_client_latency_ms"] == 120
    assert summarize(rows[1:], 1)["p50_success_client_latency_ms"] is None

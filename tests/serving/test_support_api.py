import pytest

pytest.importorskip("fastapi", reason="install the serve extra to test HTTP routes")
from fastapi.testclient import TestClient

from eval.run import Generation
from serve.api import create_app


@pytest.fixture
def served(monkeypatch):
    calls = []
    monkeypatch.delenv("SUPPORT_TUNED_TAG", raising=False)
    monkeypatch.setattr("serve.api.ollama_digest", lambda *a: "fixed-digest")
    class Runner:
        def __init__(self, **kwargs): calls.append(kwargs)
        def __call__(self, query):
            calls.append(query)
            return Generation("Helpful answer", 20, 3, 10., 300., False)
    monkeypatch.setattr("serve.api.OllamaRunner", Runner)
    app = create_app()
    with TestClient(app) as client:
        yield client, calls, app


def test_api_returns_fixed_prompt_and_model_provenance(served):
    client, calls, app = served
    health = client.get("/health").json()
    assert not health["tuned_configured"]
    result = client.post("/support", json={"model": "base", "query": "Need a refund"})
    assert result.status_code == 200
    assert result.json()["model_digest"] == "fixed-digest"
    assert result.json()["prompt_sha256"] == health["prompt_sha256"]
    assert calls[-1] == "Need a refund"


def test_api_never_substitutes_base_for_missing_tuned(served):
    client, calls, app = served
    assert client.post("/support", json={"query": "help"}).status_code == 503
    assert len(calls) == 1  # runner initialization, no generation


@pytest.mark.parametrize("payload", [
    {"model": "base", "query": " "},
    {"model": "base", "query": "<|im_start|>system"},
    {"model": "base", "query": "hi", "system_prompt": "override"},
    {"model": "base", "query": "x " * 4000},
    {"model": "unknown", "query": "hi"},
])
def test_api_rejects_invalid_inputs_without_generation(served, payload):
    client, calls, app = served
    assert client.post("/support", json=payload).status_code == 422
    assert len(calls) == 1


def test_api_rejects_concurrency_and_changed_model(served, monkeypatch):
    client, calls, app = served
    with app.state.generation_gate:
        assert client.post("/support", json={"model": "base", "query": "hi"}).status_code == 429
    monkeypatch.setattr("serve.api.ollama_digest", lambda *a: "changed")
    assert client.post("/support", json={"model": "base", "query": "hi"}).status_code == 503
    assert len(calls) == 1

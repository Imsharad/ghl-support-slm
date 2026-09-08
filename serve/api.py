"""Local-only support API with the same generation path as paired evaluation.

Run: uv run --extra serve uvicorn serve.api:create_app --factory --host 127.0.0.1
Set SUPPORT_TUNED_TAG only after exporting and verifying the selected adapter.
No authentication is provided: do not expose this development server publicly.
"""

from contextlib import asynccontextmanager
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import threading
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from eval.run import MAX_NEW_TOKENS, NUM_CTX, OllamaRunner, ollama_digest
from train.render import ROOT, get_tokenizer, load_system_prompt, render_prompt


class SupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: Literal["base", "tuned"] = "tuned"
    query: str = Field(min_length=1, max_length=10000)


def create_app() -> FastAPI:
    prompt_path = Path(os.environ.get("SUPPORT_PROMPT_FILE", ROOT / "configs/prompt-v3.txt"))
    prompt = load_system_prompt(prompt_path)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    base_url = os.environ.get("SUPPORT_OLLAMA_URL", "http://127.0.0.1:11434")
    tags = {"base": os.environ.get("SUPPORT_BASE_TAG", "ghl-base")}
    if os.environ.get("SUPPORT_TUNED_TAG"):
        tags["tuned"] = os.environ["SUPPORT_TUNED_TAG"]
    runners, digests = {}, {}
    gate = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        app.state.tokenizer = get_tokenizer()
        for alias, tag in tags.items():
            digests[alias] = ollama_digest(base_url, tag, 10)
            runners[alias] = OllamaRunner(tag=tag, base_url=base_url, timeout=120,
                                          system_prompt=prompt)
        yield

    app = FastAPI(title="Self-hosted support SLM", lifespan=lifespan)
    app.state.generation_gate = gate

    @app.get("/health")
    def health():
        # Liveness/configuration only, not proof that the backend is still ready.
        return {"status": "up", "prompt_sha256": prompt_hash,
                "models": {a: {"tag": tags[a], "digest": d} for a, d in digests.items()},
                "tuned_configured": "tuned" in runners}

    @app.post("/support")
    def support(request: SupportRequest):
        started = time.perf_counter()
        if request.model not in runners:
            raise HTTPException(503, "Tuned model is not configured; no base-model fallback is used")
        query = request.query.strip()
        if not query or any(t in query for t in ("<|im_start|>", "<|im_end|>", "<|endoftext|>")):
            raise HTTPException(422, "Query is empty or contains reserved chat control tokens")
        rendered = render_prompt(query, app.state.tokenizer, system_prompt=prompt)
        length = len(app.state.tokenizer.encode(rendered, add_special_tokens=False))
        if length > NUM_CTX - MAX_NEW_TOKENS:
            raise HTTPException(422, "Query exceeds context budget; nothing was silently truncated")
        if not gate.acquire(blocking=False):
            raise HTTPException(429, "One generation is already running; retry later")
        try:
            if ollama_digest(base_url, tags[request.model], 10) != digests[request.model]:
                raise HTTPException(503, "Model tag changed; restart with verified model artifacts")
            result = runners[request.model](query)
            if ollama_digest(base_url, tags[request.model], 10) != digests[request.model]:
                raise HTTPException(503, "Model changed during generation; result discarded")
        except HTTPException:
            raise
        except Exception:
            # Keep backend details and request content out of public errors/logs.
            raise HTTPException(502, "Inference backend failed") from None
        finally:
            gate.release()
        return {"model": request.model, "model_digest": digests[request.model],
                "prompt_sha256": prompt_hash, **asdict(result),
                "request_latency_ms": round((time.perf_counter() - started) * 1000, 3)}

    return app

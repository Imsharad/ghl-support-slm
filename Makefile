# GHL support SLM. Commands mirror docs/dag/CONTRACTS.md section 6.
# Targets may fail until the task that owns their script lands; the commands themselves are final.

.PHONY: sync test fixtures audit eval-base bench

sync:
	uv sync --frozen --extra serve

fixtures:
	uv run python data/fetch.py
	uv run python data/restore_v1.py

test:
	uv run pytest -q

audit:
	uv run python data/prepare.py --audit-only --strict

eval-base:
	uv run python eval/run.py --model base --backend ollama --split dev --check-complete

bench:
	uv run python serve/bench.py --requests 30 --concurrency 1 --check

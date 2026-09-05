# Customer-support SLM: fine-tuned Qwen2.5-1.5B-Instruct, self-hosted

Skeleton only. Every section below is filled by the tasks named in brackets; nothing here is a
result yet. The assignment brief this repo answers is at `docs/ASSIGNMENT.md`.

## 1. What this is, and the headline result

TODO (task G1)

## 2. Model and method choices, and why

TODO (task G1)

## 3. Data handling and split strategy

TODO (task G1)

## 4. Evaluation design and results

TODO (task G1)

## 5. Exact prompt template, and how to load and run

TODO (task G1)

## 6. Serving and measured latency/throughput

TODO (task G1)

## 7. Real vs cut for time, and production trade-offs

TODO (task G1)

## 8. Reproduce

TODO (task G1)

---

## Developer quickstart (task A1)

Python is pinned to 3.11 by `.python-version`; the system interpreter is 3.14 and is not used.
Everything runs through `uv run` against the locked environment.

```sh
make sync     # uv sync --frozen --extra serve
make test     # uv run pytest -q
make audit    # uv run python data/prepare.py --audit-only --strict
make eval-base
make bench
```

`bitsandbytes` lives in the `train` extra only. It has no arm64 macOS wheel, so `uv sync --extra train`
is expected to work on Colab and to fail on this Mac. The default `uv sync` and `--extra serve` both
work here.

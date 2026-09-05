# D0: Local QLoRA timing probe (Apple M1 Pro)

Question: is local QLoRA a real fallback if the cloud GPU is unavailable, or too slow to matter?

Answer: **viable fallback under 1.5 hours** for 2,000 forward/backward passes at 512 tokens.
The plan's "no local QLoRA, mlx-lm only" premise no longer holds.

Probe run 2026-09-06 00:00 IST. Start marker 2026-09-05 22:35:03 IST; the first launch died with its
tool call and produced nothing, so the measured run is the relaunched detached process (PID 97105).

## Environment

| Item | Value |
|---|---|
| Machine | Apple M1 Pro, 16 GiB unified memory, macOS 26.5 |
| Device | `mps` |
| Python | 3.11.11 (repo venv, `uv run`) |
| torch | 2.14.0 |
| transformers | 5.16.1 |
| peft | 0.20.0 |
| bitsandbytes | 0.50.2 |
| Base model | `Qwen/Qwen2.5-1.5B-Instruct` |
| Revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |

## Configuration measured

- NF4 4-bit, double quantisation, fp16 compute (`BitsAndBytesConfig`).
- LoRA r=16, alpha=32, dropout=0.05, bias none, on `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`.
- 18,464,768 trainable parameters.
- Sequence length 512, micro-batch 1, gradient checkpointing on, AdamW lr 1e-4.
- 8 synthetic sequences, 1 warmup step then 5 timed steps, `torch.mps.synchronize()` inside the timer.

## Result

```json
{"device": "mps", "seq_len": 512, "timed_steps": 5, "load_s": 7.7, "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306", "trainable_params": 18464768, "warmup_loss": [13.430027961730957], "step_times_s": [2.557, 2.559, 2.567, 2.586, 2.567], "losses": [13.2825, 13.1086, 13.0378, 12.7401, 12.7406], "loss_finite": true, "median_s_per_step": 2.567, "mean_s_per_step": 2.567, "peak_mem_gb": 4.09, "projected_2000_passes_h": 1.43, "ok": true}
```

- Median 2.567 s/step, mean 2.567 s/step. Spread across the 5 steps is 29 ms, so the number is stable.
- Peak `torch.mps.driver_allocated_memory` 4.09 GB, well inside 16 GiB. Headroom for seq 1024 or micro-batch 2.
- Losses finite throughout.
- Model load 7.7 s from a warm HF cache.

**Projected wall time:** 2,000 rows x 1 epoch, micro-batch 1, accumulation 16 = 2,000 forward/backward
passes = 2,000 x 2.567 s = **1.43 hours**. Accumulation changes optimizer-step count, not pass count,
so it does not change this figure.

## Caveat: the losses mean nothing

The probe trains on random token ids (`.scratch/qlora_probe.py` line 52, `torch.randint(0, vocab, ...)`).
The loss values sit at ln(151,936) ~ 11.9 scale and drift down because the model is memorising noise.
They are timing ballast and a finite-arithmetic check only. This probe says nothing about convergence,
data quality, or final model quality — those are D1 and C1.

Two further limits: MPS was never asked to run a kernel it might refuse beyond this shape, and no
`cpu` comparison number was taken. The CPU attempt was launched and terminated once the MPS result
landed, since the fallback-to-a-fallback was not needed.

## Verdict

Local QLoRA on this Mac is a **viable fallback**: about 1.5 hours for a 2,000-row epoch, 4.1 GB peak,
no kernel refusals. If the cloud GPU is unavailable on Tuesday, training runs here overnight rather
than blocking the schedule. Cloud remains the default for speed; this removes the single-point gate.

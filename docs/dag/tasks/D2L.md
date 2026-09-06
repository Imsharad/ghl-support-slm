# Task D2L: Local insurance training run on mps (train-t4 config, detached)

- Worker: Opus
- Phase: D
- Due (IST): Sun 2026-09-06 08:00
- Estimate: 6.0 h
- Depends on: D1, B1b
- Repo: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`
- Read first: `docs/dag/CONTRACTS.md`, then the briefs of your dependencies under `docs/dag/tasks/`, then `docs/plans/E2E_PLAN_COMPRESSED_2026-09-05-2050IST.md` section 2 and the Astra plan sections 5 and 6 for the traps and evaluation rules.

## Owned paths (write only here)

- `train/runs/local-t4/`
- `docs/LOCAL_RUN.md`

If you need a change outside these paths, describe it in your report; do not make it.

## Brief

Block 0 (Colab GPU) is still unanswered at 00:40 IST Sunday. D0 measured 2.57 s per 512-token pass on this Mac, so the
free-T4 config (cap_train 8000, one epoch) is about 5.7 h here. Run it overnight as insurance so D3 has a real adapter by
morning whatever happens with Colab. If Colab lands, the Colab run is the main run and this is the documented fallback.

Do:
- Launch detached (Popen with start_new_session, log to `train/runs/local-t4/train.log`), `--device mps`, `--data-dir data/processed`,
  `configs/train-t4.yaml` unchanged except output dir `train/runs/local-t4/`. Confirm with pgrep from a later call, then post
  the PID, the first logged step time, and the projected finish in IST. Do not wait in-turn.
- Keep the checkpoint cadence from the config so a crash loses at most 100 optimizer steps; resume with the D1 path if it dies.
- When it finishes, run `tools/check_run.py train/runs/local-t4 --max-memory-gb 12 --device mps`, plot curves, and write
  `docs/LOCAL_RUN.md`: config, wall time, peak memory, final train/val loss, checkpoint list. Commit the doc and curves.png only;
  the run directory stays untracked.
- Ollama will be serving Sol's C5 run at the same time; that is expected, do not stop it.

Verify: check_run PASS; LOCAL_RUN.md committed; the adapter path reported so D3 can pick it up.

## Rules for every task

- Work in the repo above on `main`. Commit with `git add <your paths only>` and message `D2L: <what>`; never `git add -A`; never amend or rebase; pull before commit if the index is locked, retry once.
- Run only under `uv run` in the repo venv (Python 3.11). System python is 3.14 and is off limits.
- No emojis anywhere. IST timestamps, labeled. No secrets in files (HF tokens stay in env).
- Do not start training, do not touch `eval/challenge.jsonl` after it is sealed, do not read blind keys.
- Report back in the GoHighLevel-prep thread (root `1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593`) with `@Fable 5.1`: what landed (paths), the verification command output, anything you could not do and why. One message when done or blocked; no acknowledgement messages.
- Detached jobs (anything you launch with `Popen(start_new_session=True)` or a launcher script that outlives your turn): the launcher script itself must post the finish line to this thread with `buzz messages send --channel 04861c85-e907-4639-9075-7c474cbd8b51 --reply-to 1981860808e7d870aa450555e16a336f0c9d20b710a0fee98e401b96ebf5c593 --mention c8ab0f4dfbc279dd4d4437a153d595c3a03bf710f1641e36691c888f53ba4c9d`, carrying the exit code and the result line, on both success and failure. Write that line into the script at the same time as the run command. A log file is not a callback, your session will not be awake when the job ends, and a post that mentions only yourself wakes nobody (D2L stalled 58 minutes, D3 stalled four hours on 2026-09-06).

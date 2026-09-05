#!/bin/zsh
# Resume the killed Astra planning session (thread 01a071e8-...) detached from any agent turn.
# resume rejects -p, so the model is pinned with -m (see ~/.codex/astra.config.toml).
cd /Users/sharad/Projects/agents-hq/gohighlevel-assignement-1
LOG=docs/sessions/2026-09-05-2000IST-astra-plan-resume-transcript.log
echo "start=$(date '+%Y-%m-%d %H:%M:%S %Z') pid=$$" >> "$LOG"
codex exec resume 01a071e8-b64a-7912-88aa-0a497c1dcae2 \
  -m gpt-6-astra \
  -c 'sandbox_mode="workspace-write"' \
  --skip-git-repo-check \
  -o docs/sessions/2026-09-05-2000IST-astra-plan-resume-last-message.md \
  - < docs/sessions/2026-09-05-2000IST-astra-plan-resume-prompt.md \
  >> "$LOG" 2>&1
echo "exit=$? end=$(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$LOG"

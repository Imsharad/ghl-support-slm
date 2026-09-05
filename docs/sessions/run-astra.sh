#!/bin/zsh
# Launch the Astra planning session. Transcript + last message persist under docs/sessions/.
cd /Users/sharad/Projects/agents-hq/gohighlevel-assignement-1
codex exec -p astra -s workspace-write --skip-git-repo-check \
  -C /Users/sharad/Projects/agents-hq/gohighlevel-assignement-1 \
  -o docs/sessions/2026-09-05-1950IST-astra-plan-last-message.md \
  - < docs/sessions/2026-09-05-1950IST-astra-plan-prompt.md \
  > docs/sessions/2026-09-05-1950IST-astra-plan-transcript.log 2>&1
echo "exit=$?" >> docs/sessions/2026-09-05-1950IST-astra-plan-transcript.log

#!/bin/zsh
# Launch the Astra v2 planning session detached. Transcript + last message persist under docs/sessions/.
# The finish line is posted to the GoHighLevel-prep v2 thread with a mention to Fable 5.1 (c8ab0f4d),
# on success and on failure. A log file is not a callback.
REPO=/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1
LOG=$REPO/docs/sessions/2026-09-07-1418IST-astra-v2-plan-transcript.log
LAST=$REPO/docs/sessions/2026-09-07-1418IST-astra-v2-plan-last-message.md
cd $REPO
echo "start=$(date '+%Y-%m-%d %H:%M:%S IST') pid=$$" >> $LOG
"/Users/sharad/Library/Application Support/Buzz/runtimes/node/v24.18.0/darwin-arm64/bin/codex" exec -p astra -s workspace-write --skip-git-repo-check -C $REPO -o $LAST - < docs/v2/SEED_PROMPT.md >> $LOG 2>&1
RC=$?
echo "exit=$RC end=$(date '+%Y-%m-%d %H:%M:%S IST')" >> $LOG
PLAN=$REPO/docs/plans/V2_PLAN.md
if [[ -s $PLAN ]]; then W=$(wc -w < $PLAN | tr -d ' '); PL="docs/plans/V2_PLAN.md written, $W words, sha256 $(shasum -a 256 $PLAN | cut -c1-12)"; else PL="docs/plans/V2_PLAN.md NOT written"; fi
MSG="@Fable 5.1 Astra v2 planning session finished at $(date '+%H:%M IST'), exit=$RC. $PL. Transcript docs/sessions/2026-09-07-1418IST-astra-v2-plan-transcript.log. Next: Fable reviews the plan and cuts docs/dag/v2 nodes."
printf '%s\n' "$MSG" | buzz messages send --channel 04861c85-e907-4639-9075-7c474cbd8b51 --reply-to 05b9e7942333e90470353b414345289c20836eb94901ecf7b497fb33f8e8a240 --mention c8ab0f4dfbc279dd4d4437a153d595c3a03bf710f1641e36691c888f53ba4c9d --content - >> $LOG 2>&1

---
id: ghl-slm-e2e-plan-session
title: GHL SLM assignment — end-to-end planning session (Astra)
goal: Drive one planning session that turns the GoHighLevel fine-tune-and-self-host readme into a day-by-day, gate-checked execution plan written to docs/plans/
trigger: Plan the GHL assignment end to end, launch a planning session on the readme, replan after a phase slips, re-audit the brief's decisions
status: locked
score: 92
trajectory: "v0: 58 → v1: 78 → v2: 87 → v3: 92 (plateau)"
created: 2026-09-05
updated: 2026-09-05
variables:
  - project_dir
  - readme_path
  - brief_paths
  - research_paths
  - hardware_facts
  - today_ist
  - deadline
  - plan_output_path
  - session_budget_minutes
related_projects:
  - ~/Projects/agents-hq/gohighlevel-assignement-1
tags: [ghl, slm, fine-tuning, planning, codex, astra]
---

# GHL SLM assignment — end-to-end planning session

One prompt that makes a strong planning model (Astra, or any Codex/Claude session) read the
assignment readme and the prior docs, audit the decisions already on the table, discover the
real machine and tooling, and write a single executable plan with gates. Use it to open the
first planning session and again for any replan.

## How to use

Fill the variables, then run from the project dir:
`codex exec -p astra -s workspace-write --skip-git-repo-check -C {{project_dir}} "$(cat rendered-prompt.md)"`.
Set `plan_output_path` to a fresh dated file so earlier plans stay on disk.

## Metaprompting loop (kept short)

- v0 (58): role + "read readme, write a plan". No inputs, no format, no constraints.
- v1 (78): added inputs, hard constraints, plan skeleton, variables. Still copied the brief.
- v2 (87): added audit-not-copy of the brief, read-only environment discovery, held-out-set framing, acceptance gates, unknowns list.
- v3 (92): single output file, per-phase gates with a verify command, hour estimates on IST dates, explicit stop rules (plan only, no training, no installs), Orwell prose rule. Gain under 3 points on a fourth pass, so locked.

## Master prompt

```text
<role>
You are a senior applied-ML engineer and a skeptical hiring reviewer rolled into one.
You are planning, not building. You produce one plan document a solo engineer can execute
part-time in the days that remain, and that survives a hostile code review and a follow-up
interview.
</role>

<task>
Read the hiring assignment at {{readme_path}} and write an end-to-end execution plan to
{{plan_output_path}}. The plan must cover data preparation, fine-tuning, evaluation, serving,
documentation, the Loom demo, and submission. Evaluation is the assignment's stated top
criterion, and the graders will run the model on their own internal held-out set. Plan for
that set, not for our own test split.
</task>

<inputs>
Read these before you write anything. They are prior work, not gospel.
- Assignment readme (authoritative): {{readme_path}}
- Execution brief with a decision map already drafted: {{brief_paths}}
- Research digests on current SLM fine-tuning practice and the specialist-model thesis:
  {{research_paths}}
- Machine and tooling facts, verified today: {{hardware_facts}}
- Today (IST): {{today_ist}}. Submission deadline: {{deadline}}.
The HTML files are static. Strip tags or read the text nodes; do not try to render them.
</inputs>

<constraints>
- Compute must be free (Kaggle, Colab, or the local machine). Any step that costs money is
  out. Say so wherever a paid option would have been easier.
- The model licence must permit commercial self-hosting. Name the exact checkpoint and the
  licence file you expect to find. Mark any licence claim you cannot verify offline as
  TO-VERIFY rather than asserting it.
- Do not train, download datasets or models, install packages, or write code in this session.
  You may run read-only discovery commands (ls, cat, sysctl, which, python3 -c 'import x',
  ollama list, df -h) to confirm facts about the environment. Record what you ran.
- Write only to {{plan_output_path}}. Do not modify any other file.
- Plain prose. Short words, short sentences, active voice, no jargon that the readme itself
  does not use. No emojis.
</constraints>

<method>
Think step by step, and show the reasoning in the plan where a decision is made.
1. Restate the assignment in ten lines or fewer: what is graded, what is fixed, what is open.
2. Audit the brief's decision map (model, method, data split, evaluation, serving). For each
   decision write AGREE, CHANGE, or DROP with one paragraph of reason. Do not restate a
   recommendation without testing it against the constraints, the hardware facts, and the
   research digests. If the research digests suggest something better and cheap (an adapter
   init, a judge choice, a serving stack), say whether it earns a place or is a distraction.
3. Decide where training runs (Kaggle T4, Colab T4, or local Apple silicon) and where
   serving runs. Use the hardware facts. State VRAM or unified-memory arithmetic for the
   chosen model size, quantisation, sequence length, and batch size.
4. Lay out phases in execution order. Build the evaluation harness and run the base model
   before training starts. For each phase give: goal, inputs, outputs (file paths in the
   proposed repo layout), hour estimate, IST calendar date, one acceptance gate, and the
   command or check that proves the gate. A gate that cannot be checked is not a gate.
5. List the leakage and fairness traps that apply and where in the pipeline each one is
   closed, with an assertion or test that closes it.
6. Define "better" for this task before any training numbers exist: primary metric, secondary
   metrics, judge model and family, decoding settings shared by base and tuned, sample sizes,
   how uncertainty is reported, and what result would count as a negative finding.
7. Draft the README outline in the order the assignment asks, and a 2-to-5-minute Loom shot
   list with the exact queries to show live.
8. List open questions and unknowns. For each, say who resolves it, how, and by when, and
   what the plan assumes in the meantime.
9. List cut-for-time items with a one-line reason each, so the README can report real versus
   cut honestly.
10. End with a fresh-clone checklist: the ordered commands a stranger runs from clone to a
    curl that returns a support answer.
</method>

<output_format>
Write {{plan_output_path}} as Markdown with these top-level sections, in this order:
1. Assignment in brief
2. Decision audit (table: decision | brief said | verdict | reason)
3. Compute and serving placement
4. Phase plan (one subsection per phase, with the gate and its check)
5. Traps and where each is closed
6. Evaluation design
7. README outline and Loom shot list
8. Open questions and unknowns
9. Cut for time
10. Fresh-clone checklist
11. Session log: discovery commands you ran and what they returned
Target length 1500 to 3000 words. Prefer tables to prose for anything with more than three
parallel items. Every number that comes from a source names the source.
</output_format>

<stop_rules>
Stop when the file is written and the session log is complete. Do not begin executing the
plan. If a required input file is missing or unreadable, write the plan anyway with a clear
INPUT MISSING note at the top and continue under stated assumptions. If the session runs past
{{session_budget_minutes}} minutes, write what you have with a "PARTIAL" banner at the top.
</stop_rules>
```

## Changelog

- 2026-09-05: locked at v3 (92). Written for the first Astra planning session on the GHL take-home.

## Seed

"launch an Astra session to plan how do we solve the end to end assignment reading the readme
file; craft the session master prompt using meta prompting first; persist everything under docs/"

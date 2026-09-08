# v3 execution plan

Status: Phase 0 complete; Phase 1 read-only feasibility in progress. No approval has been inferred.

## Starting evidence

- Execution seed: `docs/v3/SEED_PROMPT.md`, SHA-256 `12548db754fa66889e70e6b4697eb2968fedd13a069be54538548a93a4ce5652`.
- Source branch: `refs/heads/v2` at `f9262cc833ed579e65dbf6d87bae70d3c94126de`.
- v3 branch: `refs/heads/v3`, created directly from that source commit.
- Isolated worktree: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1-v3`.
- Source checkout: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`; it remains on `v2` and was not switched, reset, stashed, or staged.
- README start hash: `570835a9a44b037c40e7cfa3030005fc7c13b03c5afc7fdb2b11aceeb9edd8c2`.
- Existing release refs: `refs/tags/v2` is `caf0fa42dea3e84332c2b0aeb986dda6783803a3`; `refs/tags/v1` is absent at the start. No tag was created or moved.
- Required ignored analysis source: `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1/docs/analysis/why-we-failed.html`, SHA-256 `f7a881ba672294f8c57dc5a029c5ca566939b9f62cfcdb8ad322dee4715adce5`. It was read in place and not copied into v3.

The protected source checkout had these unrelated changes at branch creation:

```text
 M docs/dag/DAG.html
 M docs/dag/DAG.json
 M docs/dag/build_dag.py
?? .context/
?? artifacts/v1/adapter/
?? artifacts/v1/merged/
?? candidate_test.py
?? docs/v3/
?? test_candidates.py
?? train/runs/v2-mps/
?? train/runs/v2-t4/
```

Only the required seed was carried into the isolated worktree. The other owner files remain solely in the source checkout.

## Phase state and approval gates

| Phase | State | Gate |
|---|---|---|
| 0. Inspect and establish branch | complete | `V3-R0` records the start |
| 1. Prepare pre-registration | in progress | HARD STOP 1: owner approves `PLAN.md` and `PRE_REGISTRATION.md` |
| 2. Measurement and calibration | not started | requires HARD STOP 1 approval |
| 3. Draft/review/seal evaluation | not started | HARD STOP 2 approves exact draft hash |
| 4. Card-conditioned data | not started | requires the primary seal |
| 5. Training controls | not started | requires approved/frozen data |
| 6. Free-T4 run | not started | HARD STOP 3 approves compute launch |
| 7. Export and serve | not started | requires a guard-safe candidate |
| 8. Frozen paired evaluation | not started | requires served Q8 pair |
| 9. Results and README proposal | not started | HARD STOP 4 approves exact README patch |

README, `main`, serving files, evaluation items, training rows, model artifacts, and registered Ollama tags are unchanged.

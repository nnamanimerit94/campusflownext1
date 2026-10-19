# Agent instructions

Read README.md, ENGINEERING_PLAN.md and current GitHub issues/PRs before changes. The plan is proposed until Engineer B formally reviews and merges the planning PR; no dependent feature implementation before that gate.

Engineer A owns validation/models, ticket creation/ID/lookup/priority, notes, persistence and initial test/CI scaffolding. Engineer B's accepted ownership: lifecycle, search, reports, CLI, Engineering Understanding Check and integration verification. Confirm proposed contracts/ownership through the planning PR.

Use GitHub issues to allocate work and record dependencies. Never assume another conversation has seen a message. Use the actual reviewer account; never impersonate the other engineer or invent approval. Confirmed identities: Engineer A is nnamanimerit94; Engineer B is eeyung1. Request the other engineer's formal review and have that engineer merge.

For each task: inspect latest main and overlapping branches/issues/PRs; branch from latest main; implement the agreed scope; add meaningful invalid-input/regression tests; run relevant checks; commit/push; open a PR with evidence. Never push directly to main or merge your own PR.

The other engineer must independently review the complete current diff and tests, formally approve, verify current-head CI and merge only with no blocking unresolved feedback/conflicts. Recheck after new commits. Comments alone are not formal approvals. Do not weaken tests for green CI.

Preserve persisted data on invalid input or storage failure. Use synthetic data in public files/tests. No source/student records or secrets in commits. Update docs to reflect verified behavior, and mark pending work honestly.

Stop at genuine dependency/review/access blockers and report the exact GitHub handoff. Do not claim background work while inactive.

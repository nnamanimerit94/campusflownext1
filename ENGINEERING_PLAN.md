# CampusFlow Next engineering plan

Status: APPROVED in PR #2 (eeyung1 review 5577732703), merged as 064d5e0029cc56ac45c78fed3c8892ae033e9543. Foundation PR #4 is merged at e5534908586fac2a5f00ed94b9516a96b597d6cb. Ticket core PR #6 is merged at a71bba985d648d9a27207d8b25e42c164c352e10. Structured notes issue #7 is implemented on its feature branch, awaiting review/CI/merge.

## Objective and boundaries
A local Python campus helpdesk CLI for recording, following up and reporting student support tickets. Proposed MVP: one operator/process at a time, Python 3.11+, standard library only, JSON storage. No web UI, AI service, authentication, concurrent writers, bank integration or actual payment processing. Use synthetic student data in this public repository.

## Reconnaissance
Inspected 2026-10-19, main commit 1af93559b3802f8e85ec0fa0e1195930be316c8a. Recursive tree contains only README.md with heading "# campusflownext1". Only main exists; branch metadata reports protected=false. No issues, PRs or Actions runs existed before planning issue #1. No source, tests, dependency configuration or workflow files exist. The workflows API collection was rejected by the connector; absence of workflow files is independently established by the complete tree. No tests can currently run.

## Proposed requirements and acceptance
| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| R1 | Validated ticket creation, unique IDs and priority | Valid/invalid inputs, duplicate IDs, deterministic priority tests |
| R2 | Assignment and lifecycle | Transition matrix, reopen and failed-mutation regression tests |
| R3 | Structured notes | Author/body/timestamp validation, safe lookup tests |
| R4 | Durable JSON persistence | Round trip, malformed/schema-invalid data, failed-write preservation tests |
| R5 | Search and combined filters | Case-insensitive query, AND filters, empty results and ordering tests |
| R6 | Reports/statistics | Known fixtures, empty store, reopened tickets and totals tests |
| R7 | Interactive CLI | Realistic create/assign/note/resolve/reopen/search/report/save/reload walkthrough |
| R8 | Engineering Understanding Check | Local practice questions one at a time; deterministic rubric guidance, no claim of AI grading |
| R9 | Tests and GitHub Actions | Explicit test discovery on supported Python versions, zero-test guard, green PR/main runs |
| R10 | Accurate docs and audit evidence | Commands, limitations, PR/review/CI references and final scenario evidence |

## Proposed architecture and ownership
Use campusflow/ package, tests/, docs/, main.py entry point and .github/workflows/tests.yml.
- Engineer A: models.py (schema/validation/errors), tickets.py (creation/ID/lookup/priority), notes.py, storage.py; corresponding tests.
- Engineer B: workflow.py (assignment/lifecycle), search.py, reports.py, understanding.py, cli.py and main.py; corresponding tests and final integration verification.
- Engineer A: initial package/test/CI foundation after planning merge, preventing competing scaffolds.
- Shared documentation changes require coordination through the owning issue/PR.
Engineer B accepted this ownership split in review 5577653103; Engineer A accepts it as well.

## Version and compatibility decision
CampusFlow Next is an intentional new product version, not a drop-in continuation of the previous CampusFlow repository. Retain the explicitly listed student_id/student_name fields, categories, UUID4 ticket/note IDs and versioned JSON envelope. No legacy ID aliases, implicit category remapping or automatic old-file migration. Legacy files failing this schema raise StorageError and remain untouched. Any future import needs its own agreed contract and reviewed PR. These choices supersede accidental reliance on the old contract, approved by B in review 5577732703.

## Proposed shared data contract
TicketStore = dict[str, Ticket], keyed by ticket ID. Ticket and Note are TypedDict-shaped JSON-compatible dictionaries. No global mutable store or import-time I/O.
Ticket fields:
- id: canonical lowercase UUID4 string, generated with uuid.uuid4; collisions retry at most 10 times before raising ValidationError without mutation. Note IDs must be unique within their ticket, with the same collision policy.
- student_id, student_name, title, description: stripped nonempty strings, maximum lengths 100, 120, 200, 5000 respectively.
- category: payment | attendance | technical | welfare | other.
- urgency: low | medium | high.
- affected_users: required positive integer; reject bool, floats, numeric strings, zero and negatives.
- priority: low | medium | high | critical; derived using the priority table below, never supplied by callers. Persisted priority must match recalculation.
- status: open | in_progress | resolved | closed.
- assigned_to: null or stripped nonempty string, maximum 120.
- created_at, updated_at: timezone-aware UTC ISO 8601 strings.
- notes: list[Note]; Note fields id (UUID4), author (nonempty, max 120), body (nonempty, max 5000), created_at (UTC ISO 8601).
Only documented keys accepted in persisted records. Require exactly the documented envelope keys and integer schema_version=1 (not bool). Store keys must match ticket IDs; reject duplicate note IDs. New tickets start open with assigned_to=null, no notes and equal created_at/updated_at. Persisted in_progress/resolved/closed tickets require an assignee. Reject bool where a numeric schema version is expected. Dates must parse, updated_at >= created_at, and note timestamps cannot precede ticket creation or exceed updated_at.

IDs must be strings in canonical UUID4 format. Invalid format raises ValidationError; valid absent ID raises TicketNotFoundError. Validate entire inputs before mutation; rejected operations leave store unchanged. Public read APIs return deep copies; report/search functions never mutate inputs. Mutation APIs update the supplied in-memory store and return deep copies; persistence is explicitly invoked by the CLI.

## Proposed public interfaces
All signatures below are approved contracts, not existing functions.
- models.validate_ticket(ticket: object) -> Ticket; models.validate_store(value: object) -> TicketStore
- tickets.create_ticket(store: TicketStore, *, student_id: str, student_name: str, title: str, description: str, category: str, urgency: str, affected_users: int) -> Ticket
- tickets.get_ticket(store: TicketStore, ticket_id: str) -> Ticket
- tickets.calculate_priority(urgency: str, affected_users: int) -> str
- notes.add_note(store: TicketStore, ticket_id: str, *, author: str, body: str) -> Note
- workflow.assign_ticket(store: TicketStore, ticket_id: str, assignee: str) -> Ticket
- workflow.transition_ticket(store: TicketStore, ticket_id: str, new_status: str) -> Ticket
- workflow.reopen_ticket(store: TicketStore, ticket_id: str) -> Ticket
- storage.load_tickets(path: pathlib.Path) -> TicketStore
- storage.save_tickets(path: pathlib.Path, store: TicketStore) -> None
- search.search_tickets(store: TicketStore, *, query: str = "", status: str | None = None, priority: str | None = None, category: str | None = None, assigned_to: str | None = None) -> list[Ticket]
- reports.ticket_statistics(store: TicketStore) -> dict: total, by_status, by_priority, by_category, unassigned; enum buckets include zero counts.
- understanding.run_check(input_fn=input, output_fn=print) -> None
- cli.main() -> int; main.py invokes it only under the __main__ guard.

Errors in models.py: ValidationError(ValueError), TicketNotFoundError(LookupError), InvalidTransitionError(ValueError), StorageError(Exception). Filesystem/JSON/schema failures become StorageError preserving exception cause. Programmer errors should not be silently swallowed.

## Behavior for shared review
### Priority decision
Restore affected-user impact and critical escalation. The review does not supply the legacy threshold; the following is the explicit Next policy approved by B in review 5577732703, not a claim to reproduce unseen legacy code.

| Urgency | affected_users 1–9 | affected_users >= 10 |
| --- | --- | --- |
| low | low | medium |
| medium | medium | high |
| high | high | critical |

Validate both inputs before calculation. Test all six cells and counts 1, 9 and 10, invalid types/ranges, and persisted priority mismatches. Priority filters and report buckets must include critical. No urgency/count editing API in MVP.

### Lifecycle and follow-up decision
Notes are allowed only on open/in_progress tickets. Resolved/closed tickets must be reopened first; add_note otherwise raises InvalidTransitionError without changing timestamps or notes. Existing notes remain readable in all statuses.

| Current status | transition_ticket targets | reopen_ticket | Assign/reassign | Add note |
| --- | --- | --- | --- | --- |
| open | in_progress (assignee required) | reject | allowed | allowed |
| in_progress | resolved | reject | allowed | allowed |
| resolved | closed | open | reject | reject |
| closed | none | open | reject | reject |

transition_ticket does not accept reopening; use reopen_ticket explicitly. Valid but disallowed targets (including same status) raise InvalidTransitionError; malformed/unknown statuses raise ValidationError. Reopen preserves ID, creation time, assignee, priority and existing notes, updating only status and updated_at. Assignment requires a valid nonempty assignee; assigning the existing normalized assignee raises InvalidTransitionError. No unassign operation in MVP. Every successful mutation updates updated_at to max(current UTC time, previous updated_at), so it cannot move backwards. Test every status/target pair, both reopen sources, repeated reopen, post-reopen notes/reassignment, missing assignee and all rejected-operation immutability.
Search: stripped casefolded substring across ID, student ID/name, title, description and note bodies; empty query matches all. Supplied enum filters validate; filters combine with AND; assignee filter is stripped case-insensitive exact match. Sort by created_at then ID ascending. Blank supplied assignee is invalid.
Reports describe current state, not historical resolution counts. No deletion in MVP.
Persistence envelope: {"schema_version": 1, "tickets": [...]} with duplicate IDs rejected before converting to dict. Missing file returns empty store; empty, corrupt, unsupported-version or invalid files raise StorageError and are never silently reset. Validate entire store before saving. Write UTF-8 JSON to a temporary file in the destination directory, flush/fsync, then os.replace; clean temporary files after failure. Preserve previous target on failure before replacement. Parent directory must already exist. No file locking or guaranteed recovery from hardware/power failure.
CLI should stage mutations on a copy, save successfully, then publish the new in-memory store; failed save must not display success. User-facing validation/storage messages should preserve data and allow recovery or safe exit.

## Ordered delivery gates
1. B reviews requirements/interfaces here, records agreement via formal review, and merges planning PR. Resolve disagreements here first.
2. A: package/test/CI foundation; unittest discovery in tests/ with a guard rejecting zero discovered tests; Python 3.11 and 3.14 matrix on PRs/main pushes. B reviews/merges.
3. A: models, creation/priority/lookup and regression tests. B reviews/merges.
4. A: notes, then persistence, as separate coherent PRs. B reviews/merges each.
5. B: lifecycle; search and reports can follow merged model contract in separate branches. A reviews/merges each.
6. B: CLI and Understanding Check after required APIs merge. A reviews/merges.
7. B: integrated verification; both correct defects through reviewed PRs. Record final main SHA, CI runs, actual CLI scenarios, limitations and audit readiness.
Create one allocation issue per feature after planning approval, stating owner, dependencies, touched files and acceptance. Do not start dependent work before merge.

## Coordination and review rules
Read latest main, open issues/branches/PRs before each task. Feature branch from current main; smallest coherent PR with invalid-input/regression tests and evidence. No direct main push, self-merge, failing/conflicted/unreviewed merge or weakened tests.
The other engineer independently reads full diff, implementation and tests, checks latest head CI and unresolved reviews, formally approves and merges. Recheck after every push. A comment does not count as approval.
User-confirmed identities: Engineer A = nnamanimerit94; Engineer B = eeyung1. Review 5577653103 is authored by eeyung1, independently confirming the reviewer identity. A requests B's review and B merges A's PRs; the reverse applies to B's PRs.
Branch protection is absent; workflow compliance is procedural until a maintainer chooses repository protections. No settings changes are proposed in this PR.

## Verification and audit
Foundation test command: python scripts/run_tests.py (includes a zero-test guard). Plain discovery is also available: python -m unittest discover -s tests -v. Use temporary directories and synthetic records. Include invalid types, whitespace, malformed IDs, missing tickets, rejected-operation immutability, duplicate persisted IDs, unsupported schemas, interrupted writes and combined filters.
Final evidence must link actual CI runs and reviewed PRs, record realistic CLI save/reload scenarios, and distinguish checks run from checks merely planned.
After scope is complete, practice audit questions one at a time with human Engineer A; score /10, explain gaps and revisit weak areas. Do not claim completed audit preparation now.

## Planning review progress
2026-10-19: B requested changes in review 5577653103. A revised impact-based priority, closed-ticket note policy, full lifecycle matrix, explicit Next schema/UUID compatibility and reviewer identities. Ownership is mutually accepted; revised product contracts await B's fresh formal approval and merge of PR #2. No feature implementation or tests/CI exist yet. This documentation-only planning PR has no executable CI prerequisite; record CI as unavailable, not passed. Subsequent implementation PRs require their applicable CI checks.

## Current delivery progress
Planning PR #2, foundation PR #4 and ticket-core PR #6 are merged. Ticket-core approval: eeyung1 review 5577885442; merge a71bba985d648d9a27207d8b25e42c164c352e10; Python 3.11/3.14 CI passed.
Notes issue #7 adds notes.add_note and 12 test methods on feat/engineer-a-notes. All 33 tests pass locally on Python 3.12.14. Independent review, current-head CI and merge remain pending. Persistence is excluded and follows after notes merge. See docs/PROGRESS.md.


# CampusFlow Next engineering plan

Status: PROPOSED. Engineer B must formally review and merge the planning PR before dependent implementation. All application capabilities below are pending.

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
Assignment/lifecycle ownership fills an unallocated responsibility in the activation prompt and requires B's agreement.

## Proposed shared data contract
TicketStore = dict[str, Ticket], keyed by ticket ID. Ticket and Note are TypedDict-shaped JSON-compatible dictionaries. No global mutable store or import-time I/O.
Ticket fields:
- id: canonical lowercase UUID4 string, generated with uuid.uuid4; collisions retry before insertion.
- student_id, student_name, title, description: stripped nonempty strings, maximum lengths 100, 120, 200, 5000 respectively.
- category: payment | attendance | technical | welfare | other.
- urgency: low | medium | high; priority: low | medium | high, initially equal to validated urgency (no invented automatic escalation).
- status: open | in_progress | resolved | closed.
- assigned_to: null or stripped nonempty string, maximum 120.
- created_at, updated_at: timezone-aware UTC ISO 8601 strings.
- notes: list[Note]; Note fields id (UUID4), author (nonempty, max 120), body (nonempty, max 5000), created_at (UTC ISO 8601).
Only documented keys accepted in persisted records. Reject bool where a numeric schema version is expected. Dates must parse, updated_at >= created_at, and note timestamps cannot precede ticket creation or exceed updated_at.

IDs must be strings in canonical UUID4 format. Invalid format raises ValidationError; valid absent ID raises TicketNotFoundError. Validate entire inputs before mutation; rejected operations leave store unchanged. Public read APIs return deep copies; report/search functions never mutate inputs. Mutation APIs update the supplied in-memory store and return deep copies; persistence is explicitly invoked by the CLI.

## Proposed public interfaces
All signatures below are contracts for review, not existing functions.
- models.validate_ticket(ticket: object) -> Ticket; models.validate_store(value: object) -> TicketStore
- tickets.create_ticket(store: TicketStore, *, student_id: str, student_name: str, title: str, description: str, category: str, urgency: str) -> Ticket
- tickets.get_ticket(store: TicketStore, ticket_id: str) -> Ticket
- tickets.calculate_priority(urgency: str) -> str
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
Lifecycle: open -> in_progress -> resolved -> closed. Starting work requires an assignee. Reopen resolved/closed -> open, preserving assignee and notes. Same-status and all other transitions raise InvalidTransitionError. Reassignment allowed only on open/in_progress. Notes allowed in every status. Every successful mutation updates updated_at.
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
Engineer roles are not verified GitHub identities. B's reviewer username is currently unknown. Identify it in issue #1 before requesting an account-specific review. Two sessions using one GitHub account cannot provide formal self-approval; use a distinct authorized reviewer account.
Branch protection is absent; workflow compliance is procedural until a maintainer chooses repository protections. No settings changes are proposed in this PR.

## Verification and audit
Planned test command: python -m unittest discover -s tests -v (not available yet). Use temporary directories and synthetic records. Include invalid types, whitespace, malformed IDs, missing tickets, rejected-operation immutability, duplicate persisted IDs, unsupported schemas, interrupted writes and combined filters.
Final evidence must link actual CI runs and reviewed PRs, record realistic CLI save/reload scenarios, and distinguish checks run from checks merely planned.
After scope is complete, practice audit questions one at a time with human Engineer A; score /10, explain gaps and revisit weak areas. Do not claim completed audit preparation now.

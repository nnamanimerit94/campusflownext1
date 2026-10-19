# CampusFlow Next

A Python campus helpdesk CLI in development. Python 3.11+; standard library only.

Planning PR #2 and foundation PR #4 are merged. This ticket-core branch adds validated in-memory creation, impact-based priority, canonical UUID4 lookup and ticket/store schema validation; review/merge is pending. Lifecycle, note operations, persistence, search, reports, CLI and Understanding Check remain unimplemented.

Ticket APIs: `campusflow.tickets.create_ticket`, `calculate_priority` and `get_ticket`. Creation takes an ID-keyed store and required student_id, student_name, title, description, category, urgency and affected_users keyword arguments. Counts 1–9 retain urgency; >=10 escalates one tier (high becomes critical). Free text is stripped; enums are exact lowercase. New tickets are open/unassigned with empty notes and equal UTC timestamps. UUID allocation permits an initial candidate plus ten collision retries.

`campusflow.models.validate_ticket` and `validate_store` enforce the complete schema, including nested Note records, and return deep copies. Stored text must already be stripped; validate_store accepts an ID-keyed dictionary, not a storage envelope. Lookup raises ValidationError for malformed IDs and TicketNotFoundError for absent valid IDs. Whole-store validation prioritizes integrity over large-store lookup speed. Rejected operations preserve the store; returned objects do not alias it. No filesystem I/O or note-creation operation is implemented.

## Run the tests
From the repository root (no dependency installation required):

```sh
python scripts/run_tests.py
```

On Windows use `py` instead of `python` if needed. The runner discovers `tests/test_*.py`, rejects zero discovered tests and exits nonzero for failures/import errors. For direct discovery: `python -m unittest discover -s tests -v` (without the empty-suite guard).

GitHub Actions runs the guarded command for every pull request and pushes to main on Python 3.11 and 3.14. No application run command exists yet.

## Structure
- `campusflow/`: application package; domain modules arrive in later reviewed PRs.
- `tests/`: unittest suite.
- `scripts/run_tests.py`: local/CI runner.
- `.github/workflows/tests.yml`: CI matrix.
- `docs/PROGRESS.md`: delivery and verification evidence.

See [ENGINEERING_PLAN.md](ENGINEERING_PLAN.md) for approved contracts and ownership, [AGENTS.md](AGENTS.md) for collaboration rules, and [foundation issue #3](https://github.com/nnamanimerit94/campusflownext1/issues/3).


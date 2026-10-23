# CampusFlow Next

A **Python command-line campus helpdesk** for recording, assigning, tracking, searching and reporting student support requests. Built as a collaborative software engineering project with explicit data contracts, review-driven development and automated tests.

**Status:** Interactive CLI and core workflows are present on `main`. This is a local, single-operator learning project, not a hosted service or multi-user production system.

## Features

- **Ticket creation:** Record student details, category, urgency and affected-user count. Priority escalates one tier when 10 or more users are affected.
- **Assignment and lifecycle:** Assign tickets; move `open → in_progress → resolved → closed`; explicitly reopen resolved or closed tickets.
- **Notes:** Append validated, timestamped notes to active tickets.
- **Search:** Case-insensitive text search with optional status, priority, category and assignee filters.
- **Reports:** Current totals by status, priority and category, plus unassigned counts.
- **Persistence:** Versioned JSON storage with strict schema validation and save-before-publish CLI mutations.
- **Engineering Understanding Check:** Five practice questions with reference guidance; **not** AI grading.

## Requirements

- Python **3.11 or newer**
- No third-party dependencies for the application or its test suite

## Run the application

From the repository root:

```sh
python main.py
```

On Windows, use `py main.py` if `python` is unavailable.

The CLI shows a 12-option menu for creating, assigning and updating tickets, adding notes, searching, viewing statistics, reloading from disk, completing the practice check and exiting. Data is stored in `tickets.json` in the **current working directory**. Run the command from the repository root for predictable file placement.

When creating a ticket, choose one of these lowercase categories: `payment`, `attendance`, `technical`, `welfare`, `other`. Urgency is `low`, `medium` or `high`; `affected_users` must be a positive integer. The program generates ticket IDs; copy the displayed ID when assigning or updating a ticket.

**Important:** An invalid or corrupted existing ticket file causes a safe startup failure rather than silently resetting stored tickets. Back up `tickets.json` before experimenting with its contents.

## Run the tests

```sh
python scripts/run_tests.py
```

On Windows, `py scripts/run_tests.py` is also supported. The guarded runner discovers `tests/test_*.py`, fails on an empty test suite and returns a nonzero exit code for test failures or import errors.

Alternatively:

```sh
python -m unittest discover -s tests -v
```

GitHub Actions is configured to run the guarded test command on pull requests and pushes to `main` with Python 3.11 and 3.14. **The current test count and latest CI result should be checked in Actions; they are not claimed here.**

## Design and data integrity

The application separates its CLI from ticket operations, validation, storage, search and reporting:

| File | Responsibility |
| --- | --- |
| `main.py`, `campusflow/cli.py` | Interactive menu and save-before-publish orchestration |
| `campusflow/models.py` | Ticket/Note contracts and strict validation |
| `campusflow/tickets.py` | Ticket creation, lookup and priority calculation |
| `campusflow/notes.py` | Structured notes |
| `campusflow/workflow.py` | Assignment and status transitions |
| `campusflow/search.py` | Read-only search and combined filters |
| `campusflow/reports.py` | Read-only current-state statistics |
| `campusflow/storage.py` | Versioned JSON load and atomic file replacement |
| `campusflow/understanding.py` | Deterministic engineering practice questions |
| `tests/` | Automated tests |

The ticket store is an ID-keyed dictionary in memory. The on-disk format is a JSON object with exactly `schema_version: 1` and a `tickets` list.

Mutating CLI actions operate on a **copy** of the current store, save that copy successfully, and only then publish it in memory. Storage validates records before writing, flushes and fsyncs a temporary file in the destination directory, then uses `os.replace`. Failed writes **before replacement** preserve the previous destination file. Corrupt JSON, duplicate keys/IDs and invalid records are rejected rather than treated as an empty database.

**Limitations:** Single local operator; no authentication, concurrent-writer coordination, file locking, automatic schema migrations or guaranteed hardware/power-loss recovery. File replacement can affect destination permissions. This project is not an AI-powered helpdesk; its Understanding Check uses fixed reference guidance.

## Collaboration and contributions

The project was developed by **Engineer A ([@nnamanimerit94](https://github.com/nnamanimerit94))** and **Engineer B** through issues, pull requests, independent reviews and CI.

**Engineer A's documented contributions:**
- Project foundation, package/test structure and guarded CI runner — [PR #4](https://github.com/nnamanimerit94/campusflownext1/pull/4).
- Typed ticket models, validation and creation — [PR #6](https://github.com/nnamanimerit94/campusflownext1/pull/6).
- Structured notes and data-integrity safeguards — [PR #8](https://github.com/nnamanimerit94/campusflownext1/pull/8).
- Strict JSON persistence and atomic save behavior — [PR #10](https://github.com/nnamanimerit94/campusflownext1/pull/10).

**Engineer B's work** includes ticket lifecycle, search, reporting, the Understanding Check and interactive CLI. See the repository's pull requests for the full contribution and review history.

## Engineering documentation

- [Engineering plan](ENGINEERING_PLAN.md) — agreed contracts and ownership.
- [Collaboration guidelines](AGENTS.md) — team workflow.
- [Delivery progress](docs/PROGRESS.md) — historical implementation and verification notes. **Some entries are snapshots from earlier branches and may be outdated; use the current `main` code and PR history as the source of truth.**
- [GitHub Actions](../../actions) — check current CI runs.

## Next improvements

A short terminal demonstration, up-to-date verification summary and additional usability documentation would make this project easier to evaluate. These are documentation/presentation improvements, not claims of missing core functionality.

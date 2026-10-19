# CampusFlow Next

A Python campus helpdesk CLI in development. Python 3.11+; standard library only.

The engineering plan was approved and merged in PR #2. This foundation branch adds the package, test runner and CI; review/merge is pending. Ticket creation, lifecycle, notes, persistence, search, reports, CLI and Understanding Check remain unimplemented.

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


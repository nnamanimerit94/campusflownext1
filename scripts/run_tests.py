"""Run project tests, failing rather than silently accepting an empty suite."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Discover tests from this checkout and return a process exit status."""
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    count = suite.countTestCases()
    if count == 0:
        print("ERROR: No tests discovered in tests/.", file=sys.stderr)
        return 1
    print(f"Discovered {count} tests.", file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

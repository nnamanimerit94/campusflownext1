"""Package smoke checks and executable test-runner regression coverage."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_import_has_no_output_or_filesystem_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-B", "-c",
                 "import sys; sys.path.insert(0, sys.argv[1]); import campusflow",
                 str(ROOT)],
                cwd=directory, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            self.assertEqual(list(Path(directory).iterdir()), [])


class TestRunnerTests(unittest.TestCase):
    def run_fixture(self, source=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            shutil.copyfile(ROOT / "scripts" / "run_tests.py",
                            root / "scripts" / "run_tests.py")
            (root / "tests").mkdir()
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            if source is not None:
                (root / "tests" / "test_fixture.py").write_text(source, encoding="utf-8")
            # Running from outside the checkout also verifies path-based discovery.
            return subprocess.run(
                [sys.executable, "-B", str(root / "scripts" / "run_tests.py")],
                cwd=root.parent, capture_output=True, text=True, timeout=15,
            )

    def test_empty_suite_fails(self):
        result = self.run_fixture()
        self.assertEqual(result.returncode, 1)
        self.assertIn("No tests discovered", result.stderr)

    def test_passing_suite_succeeds(self):
        result = self.run_fixture(
            "import unittest\nclass Example(unittest.TestCase):\n"
            "    def test_ok(self): self.assertEqual(2 + 2, 4)\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 1 test", result.stderr)

    def test_assertion_failure_fails(self):
        result = self.run_fixture(
            "import unittest\nclass Example(unittest.TestCase):\n"
            "    def test_bad(self): self.fail('intentional fixture failure')\n"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED (failures=1)", result.stderr)

    def test_import_error_fails(self):
        result = self.run_fixture("raise ImportError('intentional fixture import error')\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED (errors=1)", result.stderr)


if __name__ == "__main__":
    unittest.main()

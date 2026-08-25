#!/usr/bin/env python3

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_record.py"
VALID_RECORD = ROOT / "tests" / "fixtures" / "valid-record.json"
INVALID_RECORD = ROOT / "tests" / "fixtures" / "invalid-record.json"


class ValidateRecordTests(unittest.TestCase):
    def run_validator(self, record: Path):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(record)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_record_is_accepted(self):
        result = self.run_validator(VALID_RECORD)

        self.assertEqual(result.returncode, 0)
        self.assertIn("VALID:", result.stdout)

    def test_invalid_record_is_rejected(self):
        result = self.run_validator(INVALID_RECORD)

        self.assertEqual(result.returncode, 1)
        self.assertIn("INVALID:", result.stdout)
        self.assertIn("difficulty", result.stdout)
        self.assertIn("god-mode", result.stdout)


if __name__ == "__main__":
    unittest.main()

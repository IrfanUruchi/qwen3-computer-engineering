#!/usr/bin/env python3

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_dataset.py"

FIXTURES = ROOT / "tests" / "fixtures"

VALID_DATASET = FIXTURES / "valid-dataset.jsonl"
DUPLICATE_DATASET = FIXTURES / "duplicate-id-dataset.jsonl"
MALFORMED_DATASET = FIXTURES / "malformed-dataset.jsonl"
REJECTED_DATASET = FIXTURES / "rejected-dataset.jsonl"


class ValidateDatasetTests(unittest.TestCase):
    def run_validator(self, dataset: Path):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(dataset)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_dataset_is_accepted(self):
        result = self.run_validator(VALID_DATASET)

        self.assertEqual(result.returncode, 0)
        self.assertIn("VALID:", result.stdout)
        self.assertIn("(2 records)", result.stdout)

    def test_duplicate_id_is_rejected(self):
        result = self.run_validator(DUPLICATE_DATASET)

        self.assertEqual(result.returncode, 1)
        self.assertIn("INVALID:", result.stdout)
        self.assertIn("duplicate id", result.stdout)
        self.assertIn(
            "ce-linux-systemd-debug-000001",
            result.stdout,
        )

    def test_malformed_json_is_rejected(self):
        result = self.run_validator(MALFORMED_DATASET)

        self.assertEqual(result.returncode, 1)
        self.assertIn("INVALID:", result.stdout)
        self.assertIn("invalid JSON", result.stdout)

    def test_rejected_record_is_rejected(self):
        result = self.run_validator(REJECTED_DATASET)

        self.assertEqual(result.returncode, 1)
        self.assertIn("INVALID:", result.stdout)
        self.assertIn(
            "rejected record present in dataset",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()

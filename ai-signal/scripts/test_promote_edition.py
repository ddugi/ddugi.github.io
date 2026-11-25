#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

promote = load("promote", ROOT / "scripts" / "promote_edition.py")
REVIEW = json.loads((ROOT / "content" / "review" / "edition-01.json").read_text())
LIVE = json.loads((ROOT / "content" / "publication.json").read_text())

class PromoteEditionTests(unittest.TestCase):
    def test_candidate_uses_review_edition_number_and_date(self):
        review = copy.deepcopy(REVIEW)
        review["edition"]["id"] = "edition-02"
        review["edition"]["publicationDate"] = "2026-09-25"
        result = promote.candidate(review, LIVE)
        self.assertEqual(result["publication"]["edition"], "02")
        self.assertEqual(result["publication"]["updatedAt"], "2026-09-25")
        self.assertIn("Edition 02", result["signalMap"]["note"])
        self.assertEqual(result["weekly"]["slug"], "2026-09-25")

if __name__ == "__main__":
    unittest.main()

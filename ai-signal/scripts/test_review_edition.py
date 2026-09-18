#!/usr/bin/env python3
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review", ROOT / "scripts" / "review_edition.py")
review = importlib.util.module_from_spec(spec); spec.loader.exec_module(review)
DATA = json.loads((ROOT / "content" / "review" / "edition-01.json").read_text())

class ReviewEditionTests(unittest.TestCase):
    def test_current_drafts_validate_and_render(self):
        review.validate(DATA)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "edition"
            review.build(DATA, output)
            self.assertTrue((output / "index.html").is_file())
            for story in DATA["stories"]:
                page = output / "stories" / story["slug"] / "index.html"
                self.assertTrue(page.is_file())
                text = page.read_text()
                self.assertIn("LOCAL EDITORIAL REVIEW", text)
                self.assertIn("Conditional outlook", text)

    def test_pending_story_blocks_release(self):
        with self.assertRaisesRegex(ValueError, "approval missing"):
            review.validate(DATA, ready=True)

    def test_unresolved_fact_source_is_rejected(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["facts"][0]["sourceIds"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "resolve"):
            review.validate(data)

    def test_non_primary_or_undated_source_is_rejected(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["sources"][0]["kind"] = "secondary"
        with self.assertRaisesRegex(ValueError, "primary"):
            review.validate(data)
        data = copy.deepcopy(DATA)
        data["stories"][0]["sources"][0]["publishedAt"] = None
        with self.assertRaisesRegex(ValueError, "exact"):
            review.validate(data)

    def test_prediction_label_is_required(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["outlook"] = "This will definitely happen."
        with self.assertRaisesRegex(ValueError, "conditional"):
            review.validate(data)

    def test_map_change_requires_story(self):
        data = copy.deepcopy(DATA)
        data["signalMapChanges"][0]["storyId"] = "missing"
        with self.assertRaisesRegex(ValueError, "resolve"):
            review.validate(data)

if __name__ == "__main__":
    unittest.main()

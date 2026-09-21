#!/usr/bin/env python3
"""Meaningful content, safety, publishing-gate and generated-link checks."""
import copy
import importlib.util
import json
import re
import unittest
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("signal_build", ROOT / "scripts/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
DATA = json.loads((ROOT / "content/publication.json").read_text())
UPDATE_STATE = json.loads((ROOT / "content/update-state.json").read_text())

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.h1 = [], [], 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.append(a["id"])
        if tag == "h1": self.h1 += 1
        if tag in ("a", "link", "script"):
            value = a.get("href", a.get("src", ""))
            if value: self.links.append(value)

class PublicationTests(unittest.TestCase):
    def test_update_state_contract(self):
        state = UPDATE_STATE
        self.assertEqual(state["schema_version"], 1)
        self.assertIsInstance(state["initial_lookback_days"], int)
        self.assertGreater(state["initial_lookback_days"], 0)
        timestamp = state["last_successful_update"]
        if timestamp is not None:
            self.assertTrue(timestamp.endswith("Z"))
            datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
        commit = state["last_successful_commit"]
        self.assertTrue(commit is None or re.fullmatch(r"[0-9a-f]{40}", commit))
        published_ids = state["last_published_story_ids"]
        self.assertEqual(len(published_ids), len(set(published_ids)))
        stories = {story["id"]: story for story in DATA["stories"]}
        self.assertTrue(all(story_id in stories for story_id in published_ids))
        self.assertTrue(all(stories[story_id]["status"] == "published" for story_id in published_ids))

    def test_demo_content_is_explicit(self):
        build.validate(DATA)
        pages = build.build(DATA)
        for story in DATA["stories"]:
            self.assertEqual(story["facts"], [])
            page = pages[f'stories/{story["slug"]}/index.html']
            self.assertIn("Editorial demonstration, not a news report", page)
            self.assertIn("No verified news facts are asserted", page)
            self.assertIn("Conditional outlook", page)

    def test_unreviewed_reporting_cannot_publish(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["status"] = "published"
        with self.assertRaisesRegex(ValueError, "requires verified facts"):
            build.validate(data)

    def test_fact_source_resolution(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["status"] = "draft"
        data["stories"][0]["facts"] = [{"text":"Claim", "sourceIds":["missing"], "verifiedAt":"2026-09-18"}]
        with self.assertRaisesRegex(ValueError, "unresolved sources"):
            build.validate(data)

    def test_review_required_with_valid_sources(self):
        data = copy.deepcopy(DATA)
        story = data["stories"][0]
        story["status"] = "published"
        story["facts"] = [{"text":"A sample fact record.", "sourceIds":["source-1"], "verifiedAt":"2026-09-18"}]
        story["sources"] = [{"id":"source-1", "title":"Example only", "publisher":"Example", "url":"https://example.com/", "publishedAt":None, "accessedAt":"2026-09-18"}]
        with self.assertRaisesRegex(ValueError, "editorial approval"):
            build.validate(data)
        story["review"] = {"status":"approved", "reviewer":"Test reviewer", "reviewedAt":"2026-09-18"}
        build.validate(data)

    def test_unsafe_urls_and_paths_rejected(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["slug"] = "../../outside"
        with self.assertRaisesRegex(ValueError, "Unsafe story slug"):
            build.validate(data)
        data = copy.deepcopy(DATA)
        data["stories"][0]["sources"] = [{"id":"bad", "title":"Bad", "publisher":"Bad", "url":"javascript:alert(1)", "publishedAt":None, "accessedAt":"2026-09-18"}]
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            build.validate(data)

    def test_duplicate_and_unresolved_references(self):
        data = copy.deepcopy(DATA)
        data["stories"].append(data["stories"][0])
        with self.assertRaisesRegex(ValueError, "unique"):
            build.validate(data)
        data = copy.deepcopy(DATA)
        data["signalMap"]["items"][0]["storyId"] = "missing"
        with self.assertRaisesRegex(ValueError, "reference"):
            build.validate(data)

    def test_html_is_escaped(self):
        data = copy.deepcopy(DATA)
        data["stories"][0]["title"] = '<script>alert("x")</script>'
        pages = build.build(data)
        self.assertNotIn('<script>alert("x")</script>', pages["index.html"])
        self.assertIn("&lt;script&gt;", pages["index.html"])

    def test_drafts_do_not_generate_pages(self):
        data = copy.deepcopy(DATA)
        removed = data["stories"][-1]
        removed["status"] = "draft"
        self.assertNotIn(f'stories/{removed["slug"]}/index.html', build.build(data))

    def test_reading_time_is_derived(self):
        original = DATA["stories"][0]
        longer = copy.deepcopy(original)
        longer["analysis"] += " extra" * 500
        self.assertGreater(build.read_minutes(longer), build.read_minutes(original))

    def test_links_headings_and_sections(self):
        pages = build.build(DATA)
        parsed = {}
        for relative, content in pages.items():
            p = Page(); p.feed(content); parsed[(ROOT / relative).resolve()] = p
            self.assertEqual(p.h1, 1, relative)
            self.assertEqual(len(p.ids), len(set(p.ids)), relative)
        for path, page in parsed.items():
            for link in page.links:
                url = urlsplit(link)
                if url.scheme or url.netloc: continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                if target.is_dir() or url.path.endswith("/"): target = target / "index.html"
                self.assertTrue(target.exists() or target in parsed, (path, link))
                if url.fragment:
                    target_page = parsed.get(target)
                    if target_page is None:
                        target_page = Page(); target_page.feed(target.read_text())
                    self.assertIn(url.fragment, target_page.ids, (path, link))

if __name__ == "__main__":
    unittest.main()

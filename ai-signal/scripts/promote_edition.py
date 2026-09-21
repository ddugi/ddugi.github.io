#!/usr/bin/env python3
"""Create a publication candidate from a fully approved review edition."""
from pathlib import Path
import argparse
import copy
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
REVIEW_SOURCE = ROOT / "content" / "review" / "edition-01.json"
LIVE_SOURCE = ROOT / "content" / "publication.json"
CANDIDATE = ROOT / ".review" / "edition-01" / "publication-candidate.json"

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

reviewer = load_module("review_edition", ROOT / "scripts" / "review_edition.py")
builder = load_module("signal_build", ROOT / "scripts" / "build.py")

def candidate(review, current):
    reviewer.validate(review, ready=True)
    publish_date = review["edition"]["publicationDate"]
    result = copy.deepcopy(current)
    result["publication"].update({"edition": "01", "mode": "live", "updatedAt": publish_date})
    result["stories"] = []
    for draft in review["stories"]:
        story = copy.deepcopy(draft)
        story["status"] = "published"
        story["updatedAt"] = publish_date
        story["review"] = {
            "status": "approved",
            "reviewer": draft["review"]["reviewer"],
            "reviewedAt": draft["review"]["reviewedAt"]
        }
        for source in story["sources"]:
            source.pop("kind", None)
        result["stories"].append(story)
    changes = {x["area"]: x for x in review["signalMapChanges"]}
    result["signalMap"].update({
        "status": "editorial",
        "asOf": publish_date,
        "note": "Directional editorial assessment based only on the linked stories in Edition 01. Arrows are qualitative, not quantitative scores."
    })
    for item in result["signalMap"]["items"]:
        if item["area"] in changes:
            item.update(changes[item["area"]])
        else:
            item.update({"direction": "flat", "dimension": "No new assessment", "rationale": "Edition 01 proposes no evidence-backed movement for this area.", "storyId": None})
    weekly = review["weekly"]
    result["weekly"] = {
        "slug": publish_date,
        "title": weekly["title"],
        "date": publish_date,
        "status": "published",
        "intro": weekly["intro"],
        "theme": weekly["theme"],
        "storyIds": [x["id"] for x in result["stories"]],
        "watchNext": weekly["watchNext"],
        "closing": weekly["closing"]
    }
    builder.validate(result)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Replace the live source after all review gates pass")
    args = parser.parse_args()
    review = json.loads(REVIEW_SOURCE.read_text(encoding="utf-8"))
    current = json.loads(LIVE_SOURCE.read_text(encoding="utf-8"))
    result = candidate(review, current)
    target = LIVE_SOURCE if args.apply else CANDIDATE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    action = "updated live publication source" if args.apply else "wrote review-only publication candidate"
    print(f"PASS: {action}: {target}")

if __name__ == "__main__":
    main()

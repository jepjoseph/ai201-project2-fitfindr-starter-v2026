"""Measure the fixed graphic-tee search before and after one change."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_client import call_tool

if len(sys.argv) != 2 or sys.argv[1] not in ("before", "after"):
    raise SystemExit(
        "Usage: python results/search_relevance_check.py before|after"
    )

label = sys.argv[1]
arguments = {
    "description": "graphic tee",
    "size": None,
    "max_price": 30.0,
}

# Reviewed tee listings in the baseline results.
# Keep this reference set unchanged for the after measurement.
expected_tee_ids = {"lst_002", "lst_006", "lst_033"}

results = call_tool("search_listings", arguments)
returned_ids = {item["id"] for item in results}
relevant_count = sum(
    item["id"] in expected_tee_ids for item in results
)

record = {
    "produced_by": "results/search_relevance_check.py",
    "search_transport": "mcp_client.call_tool",
    "label": label,
    "arguments": arguments,
    "expected_tee_ids": sorted(expected_tee_ids),
    "results": [
        {
            "id": item["id"],
            "title": item["title"],
            "description": item["description"],
            "price": item["price"],
        }
        for item in results
    ],
    "result_count": len(results),
    "relevant_count": relevant_count,
    "precision": relevant_count / len(results) if results else None,
    "all_three_reference_tees_returned": (
        expected_tee_ids.issubset(returned_ids)
    ),
    "tighter_target_met": (
        bool(results) and returned_ids.issubset(expected_tee_ids)
    ),
}

text = json.dumps(record, indent=2, ensure_ascii=False)
path = ROOT / "results" / f"search_relevance_{label}.json"
path.write_text(text, encoding="utf-8")

print(text)
print(f"\nSaved: {path}")
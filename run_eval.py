#!/usr/bin/env python3
"""
Run your scenarios repeatedly and write the results down. ← UNIT 4

    python run_eval.py --label before      five tries, the default
    python run_eval.py --label after       after your improvement
    python run_eval.py --tries 10          more tries

This does the mechanical half of unit 4 for you. It runs every scenario in
`scenarios.py` five separate times, **with caching off** so you get five real
answers, captures the trace and the session for each, and writes it all into
`results/` in the table format the submission asks for.

Five, because your criteria are written out of five — "4 of 5 tries", "5 of 5
tries". One column per try means you count the passes and read the verdict
straight off the row, with no arithmetic in between.

⚠️ What it does NOT do is decide whether a try passed.

That judgment is yours, and it has to be, because it depends on criteria you
wrote. The Verdict column comes out blank and you fill it in from the output
underneath. Deciding what counts as a pass is the lesson — a scorer handed to
you would teach you nothing.

**Two of your three tools call a model, so tries will legitimately differ.**
That is expected here, unlike pair 1. If all five tries come back identical
on a criterion that involves the fit card, check that you're really in test
mode — caching is what usually explains it.

Runs five trials per scenario with caching disabled.
PASS/FAIL and verdicts remain yours to decide from the recorded evidence.
"""

import argparse
from copy import deepcopy
import datetime as dt
import json
import sys
import traceback
from unittest.mock import patch

import config
import scenarios as scenario_module


def run_once(scenario, attempt=1, use_trace=True):
    """Execute one trial and capture its session, trace, and observations."""
    import agent
    import tools
    import trace as trace_module
    from mcp_client import call_tool
    from utils.data_loader import (
        get_example_wardrobe,
        get_empty_wardrobe,
        load_listings,
    )

    if use_trace:
        trace_module.start_trace()

    record = {
        "error": None,
        "session": None,
        "trace": "",
        "crashed": None,
        "calls": [],
        "evidence": {},
    }

    try:
        kind = scenario.get("kind", "agent")

        if kind in ("agent", "state"):
            wardrobe = (
                get_empty_wardrobe()
                if scenario["wardrobe"] == "empty"
                else get_example_wardrobe()
            )

            original_new_session = agent.new_session
            original_search = agent.call_tool
            original_outfit = agent.suggest_outfit
            original_card = agent.create_fit_card
            active_session = {}

            def observe_session(query, wardrobe):
                session = original_new_session(query, wardrobe)
                active_session["value"] = session
                return session

            def observe_search(name, arguments):
                call = {
                    "tool": name,
                    "transport": "MCP",
                    "completed": False,
                }
                record["calls"].append(call)
                result = original_search(name, arguments)
                call["completed"] = True
                return result

            def observe_outfit(new_item, wardrobe):
                call = {
                    "tool": "suggest_outfit",
                    "completed": False,
                }
                record["calls"].append(call)

                # Compare independent snapshots at tool entry.
                selected = deepcopy(
                    active_session["value"]["selected_item"]
                )
                received = deepcopy(new_item)
                record["evidence"].update({
                    "selected_item_at_outfit_entry": selected,
                    "new_item_received": received,
                    "dictionaries_equal": selected == received,
                })

                result = original_outfit(new_item, wardrobe)
                call["completed"] = True
                return result

            def observe_card(outfit, new_item):
                call = {
                    "tool": "create_fit_card",
                    "completed": False,
                }
                record["calls"].append(call)
                result = original_card(outfit, new_item)
                call["completed"] = True
                return result

            # These wrappers observe the real calls; they do not replace
            # returned listings or model responses with invented values.
            with (
                patch.object(agent, "new_session", observe_session),
                patch.object(agent, "call_tool", observe_search),
                patch.object(agent, "suggest_outfit", observe_outfit),
                patch.object(agent, "create_fit_card", observe_card),
            ):
                record["session"] = agent.run_agent(
                    scenario["query"], wardrobe
                )

        elif kind == "fit_card":
            listing = next(
                item for item in load_listings()
                if item["id"] == scenario["listing_id"]
            )
            record["evidence"] = {
                "listing": deepcopy(listing),
                "outfit": scenario["outfit"],
            }

            call = {"tool": "create_fit_card", "completed": False}
            record["calls"].append(call)
            caption = tools.create_fit_card(
                scenario["outfit"], deepcopy(listing)
            )
            call["completed"] = True

            record["evidence"].update({
                "caption": caption,
                "word_count": len(caption.split()),
                "full_title_present": (
                    listing["title"].casefold() in caption.casefold()
                ),
                "platform_present": (
                    listing["platform"].casefold() in caption.casefold()
                ),
                "expected_price": listing["price"],
            })

        elif kind == "price":
            case = scenario["cases"][attempt - 1]
            arguments = {
                "description": case["description"],
                "size": None,
                "max_price": case["max_price"],
            }
            record["evidence"]["arguments"] = arguments

            call = {
                "tool": "search_listings",
                "transport": "MCP",
                "completed": False,
            }
            record["calls"].append(call)
            results = call_tool("search_listings", arguments)
            call["completed"] = True

            record["evidence"].update({
                "results": results,
                "result_count": len(results),
                "non_empty": bool(results),
                "all_prices_within_ceiling": all(
                    item["price"] <= case["max_price"]
                    for item in results
                ),
            })

        else:
            raise ValueError(f"Unknown scenario kind: {kind}")

    except Exception as exc:
        record["crashed"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()

    finally:
        if use_trace:
            record["trace"] = trace_module.get_trace()

    return record


def main():
    parser = argparse.ArgumentParser(
        description="Run the scenarios and log the results."
    )
    parser.add_argument(
        "--tries", "--trials",
        type=int,
        default=5,
        dest="tries",
        help="five trials, matching the original criteria",
    )
    parser.add_argument("--label", default="")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate inputs without executing trials",
    )
    args = parser.parse_args()

    problems = scenario_module.validate()
    if problems:
        print("scenarios.py has problems:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        sys.exit(1)

    if not scenario_module.SCENARIOS:
        sys.exit("scenarios.py is empty.")

    # Criterion 5 defines exactly five distinct search cases.
    if args.tries != 5:
        parser.error(
            "This evaluation uses exactly five trials per scenario, "
            "matching criteria.md and the five price-search cases."
        )

    if args.check:
        print(
            "Five criterion scenarios and the empty-wardrobe "
            "diagnostic validated. No model calls made."
        )
        return

    config.CACHE_ENABLED = False
    print("Cache is OFF for this run — that's deliberate.\n")

    rows = []
    for scenario in scenario_module.SCENARIOS:
        print(scenario["name"])

        if "query" in scenario:
            print(f"  query: {scenario['query']}")

        tries = []
        for attempt in range(1, args.tries + 1):
            record = run_once(scenario, attempt)
            tries.append(record)

            if record["crashed"]:
                print(
                    f"  try {attempt}: CRASHED — "
                    f"{record['crashed']}"
                )
            else:
                session = record["session"] or {}
                if session.get("error"):
                    print(
                        f"  try {attempt}: stopped early — "
                        f"{session['error']}"
                    )
                else:
                    print(
                        f"  try {attempt}: evidence recorded "
                        "(not yet scored)"
                    )

        rows.append({"scenario": scenario, "tries": tries})
        print()

    write_report(rows, args)


def write_report(rows, args):
    """Preserve the starter table and append complete trial evidence."""
    import generate

    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"run_{stamp}{label}.md"

    n = args.tries
    headers = " | ".join(f"Try {i}" for i in range(1, n + 1))
    divider = "|".join(["---"] * n)

    lines = [
        f"# Run log{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `run_eval.py::main` and "
        "`run_eval.py::write_report`",
        "- Observations: `run_eval.py::run_once`",
        "- Loop: `agent.py::run_agent` · tools: `tools.py`",
        "- Search transport: `mcp_client.py::call_tool` → "
        "`mcp_server.py::search_listings`",
        f"- Tries per scenario: {n}, caching off",
        f"- Temperature: {config.TEMPERATURE}",
        f"- When: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"- Usage: {generate.usage()}",
        "",
        "Fill in targets from criteria.md, then judge each trial using",
        "the output below. The diagnostic row is not a sixth criterion.",
        "",
        f"| Criterion | Target | {headers} | Verdict |",
        f"|---|---|{divider}|---|",
    ]

    for row in rows:
        scenario = row["scenario"]
        number = scenario.get("criterion")
        label_text = (
            f"{number}. {scenario['name']}"
            if number is not None
            else f"{scenario['name']} _(diagnostic — not one of your five)_"
        )
        lines.append(
            f"| {label_text} |  | {' | '.join([' '] * n)} |  |"
        )

    lines += [
        "",
        "> Try and Verdict columns are blank on purpose.",
        "> A target of 4/5 requires at least four passing trials;",
        "> a target of 5/5 requires all five.",
        "",
        "Criterion 4 uses identical listing and outfit inputs each time.",
        "Criterion 5 executes a different predefined search on each trial.",
        "Tool-call observations distinguish attempted and completed calls.",
        "Caption price formatting must be checked against the real caption.",
        "",
        "---",
        "",
        "## What actually happened",
        "",
        "Real output and observations recorded by `run_eval.py::run_once`.",
        "",
    ]

    for row in rows:
        scenario = row["scenario"]
        lines += [
            f"### {scenario['name']}",
            "",
            "Scenario inputs:",
            "```json",
            json.dumps(scenario, indent=2, ensure_ascii=False),
            "```",
            "",
        ]

        for attempt, record in enumerate(row["tries"], 1):
            lines += [f"**Try {attempt}**", ""]

            if record["crashed"]:
                lines += [
                    "Crashed:",
                    "```text",
                    record["crashed"],
                    "```",
                    "",
                ]

            session = record["session"] or {}
            if record["session"] is not None:
                item = session.get("selected_item") or {}
                lines += [
                    f"- stopped early: "
                    f"{session.get('error') or 'no'}",
                    f"- selected_item: "
                    f"{item.get('title', '(none)')}",
                    f"- search_results: "
                    f"{len(session.get('search_results') or [])}",
                    "",
                ]

                if session.get("outfit_suggestion"):
                    lines += [
                        "Outfit suggestion:",
                        "```text",
                        str(session["outfit_suggestion"]),
                        "```",
                        "",
                    ]

                if session.get("fit_card"):
                    lines += [
                        "Fit card:",
                        "```text",
                        str(session["fit_card"]),
                        "```",
                        "",
                    ]

            lines += [
                "Tool calls and measurement evidence:",
                "```json",
                json.dumps(
                    {
                        "calls": record["calls"],
                        "evidence": record["evidence"],
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                "```",
                "",
            ]

            if record["trace"]:
                lines += [
                    "Trace:",
                    "```text",
                    record["trace"],
                    "```",
                    "",
                ]

    path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nWrote {path.relative_to(config.ROOT)}")
    print(generate.usage())
    print("\nCommit this file after reviewing the evidence.")


if __name__ == "__main__":
    main()
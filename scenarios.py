"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.

The "kind" field tells the evaluator what to execute:
- agent: a complete agent query
- state: an agent query with dictionary-transfer observations
- fit_card: create_fit_card with the same fixed inputs each time
- price: one of five predefined price-filter searches

These inputs are fixed before collecting baseline results.
"""

SCENARIOS = [
    {
        "name": "matching query completes",
        "kind": "agent",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        "name": "impossible query stops early",
        "kind": "agent",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        "name": "empty wardrobe",
        "kind": "agent",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        "name": "selected item reaches outfit tool unchanged",
        "kind": "state",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "fit card includes details and stays short",
        "kind": "fit_card",
        "listing_id": "lst_002",
        "outfit": (
            "Style the butterfly-print baby tee with baggy dark-wash "
            "jeans, chunky white sneakers, and a black crossbody bag."
        ),
        "criterion": 4,
    },
    {
        "name": "search respects the price ceiling",
        "kind": "price",
        "cases": [
            {"description": "graphic tee", "max_price": 30.0},
            {"description": "jeans", "max_price": 40.0},
            {"description": "jacket", "max_price": 50.0},
            {"description": "mesh", "max_price": 15.0},
            {"description": "hoodie", "max_price": 30.0},
        ],
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Check scenario inputs without making model calls."""
    from utils.data_loader import load_listings

    problems = []
    listings = load_listings()

    for index, scenario in enumerate(SCENARIOS, 1):
        kind = scenario.get("kind", "agent")
        label = f"scenario {index}"

        if kind in ("agent", "state"):
            if not scenario.get("query", "").strip():
                problems.append(f"{label} has no query")

            if scenario.get("wardrobe") not in WARDROBES:
                problems.append(
                    f"{label} has wardrobe "
                    f"{scenario.get('wardrobe')!r} — "
                    f"it should be one of {WARDROBES}"
                )

        elif kind == "fit_card":
            matches = [
                item
                for item in listings
                if item["id"] == scenario.get("listing_id")
            ]

            if len(matches) != 1:
                problems.append(
                    f"{label}: listing_id must identify exactly one listing"
                )

            if not scenario.get("outfit", "").strip():
                problems.append(f"{label}: outfit must be non-empty")

        elif kind == "price":
            cases = scenario.get("cases", [])

            if len(cases) != 5:
                problems.append(
                    f"{label}: criterion 5 requires five searches"
                )

            for case in cases:
                description = case.get("description", "").strip()
                ceiling = case.get("max_price")

                if not description:
                    problems.append(f"{label}: search description is empty")
                    continue

                if (
                    isinstance(ceiling, bool)
                    or not isinstance(ceiling, (int, float))
                    or ceiling < 0
                ):
                    problems.append(
                        f"{label}: max_price must be a non-negative number"
                    )
                    continue

                words = set(description.casefold().split())

                # Verify the precondition from the dataset, independently
                # of the search function being evaluated.
                eligible = [
                    item
                    for item in listings
                    if item["price"] <= ceiling
                    and words.issubset(
                        set(
                            str(item["description"])
                            .casefold()
                            .split()
                        )
                    )
                ]

                if not eligible:
                    problems.append(
                        f"{label}: verify an in-budget description match "
                        f"for {description!r} at ${ceiling:.2f}"
                    )

        else:
            problems.append(f"{label} has unknown kind {kind!r}")

    return problems
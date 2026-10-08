"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import config
import trace
import re
from tools import suggest_outfit, create_fit_card
from mcp_client import call_tool, MCPError
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """Run the tools through session state, stopping when search is empty."""
    session = new_session(query, wardrobe)

    description = query.strip()

    price_match = re.search(
        r"\bunder\s+\$?(\d+(?:\.\d+)?)\b",
        description,
        re.IGNORECASE,
    )
    max_price = float(price_match.group(1)) if price_match else None
    if price_match:
        description = (
            description[:price_match.start()]
            + " "
            + description[price_match.end():]
        )

    size_match = re.search(
        r"\bsize\s+((?:US\s+)?\d+(?:\.\d+)?"
        r"|W\d+(?:\s+L\d+)?"
        r"|XXXL|XXL|XXS|XL|XS|[SML](?:/[SML])?)\b",
        description,
        re.IGNORECASE,
    )
    size = size_match.group(1).upper() if size_match else None
    if size_match:
        description = (
            description[:size_match.start()]
            + " "
            + description[size_match.end():]
        )

    description = re.sub(
        r"^\s*(?:looking for\s+|find me\s+)",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\b(?:in|a|an)\b", " ", description, flags=re.IGNORECASE)
    description = re.sub(r"\s+", " ", description).strip(" ,")

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    trace.step(
        "parse query",
        inputs=query,
        returned=str(session["parsed"]),
    )

    stage = "search"
    iterations = 0

    try:
        while True:
            iterations += 1
            trace.check_iterations(iterations)

            if stage == "search":
                trace.step(
                    "search_listings (via MCP): calling",
                    inputs=str(session["parsed"]),
                )

                session["search_results"] = call_tool(
                    "search_listings",
                    session["parsed"],
                )

                trace.step(
                    "search_listings (via MCP): returned",
                    returned=session["search_results"],
                )

                if not session["search_results"]:
                    session["error"] = (
                        "No matching listings. Try broadening the description, "
                        "choosing another size, or increasing the price ceiling."
                    )
                    trace.step(
                        "empty-search branch",
                        note="No listings; stop before suggest_outfit.",
                    )
                    return session

                session["selected_item"] = session["search_results"][0]
                trace.step(
                    "select listing",
                    returned=session["selected_item"],
                    note="Use the first ranked result for the outfit.",
                )
                stage = "outfit"

            elif stage == "outfit":
                wardrobe_items = session["wardrobe"].get("items", [])

                trace.step(
                    "suggest_outfit: calling",
                    inputs=session["selected_item"],
                    note=(
                        f"Wardrobe contains {len(wardrobe_items)} items."
                        if wardrobe_items
                        else (
                            "Empty wardrobe: request general styling advice "
                            "without claiming suggested pieces are owned."
                        )
                    ),
                )

                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"],
                    session["wardrobe"],
                )

                trace.step(
                    "suggest_outfit: returned",
                    returned=session["outfit_suggestion"],
                )
                stage = "fit_card"

            elif stage == "fit_card":
                trace.step(
                    "create_fit_card: calling",
                    inputs=session["selected_item"],
                    note="Use the outfit suggestion stored in the session.",
                )

                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"],
                    session["selected_item"],
                )

                trace.step(
                    "create_fit_card: returned",
                    returned=session["fit_card"],
                    note="Fit card complete; stop.",
                )
                return session

    except ModelUnavailable as exc:
        session["error"] = (
            f"Could not complete the {stage} stage. {exc}"
        )
        trace.step(
            "model unavailable",
            note=f"Failed during {stage}; stop without retrying downstream tools.",
        )
        return session

    except MCPError:
        session["error"] = (
            "Could not search listings through MCP. "
            "Run python mcp_client.py to check the server, then try again."
        )
        trace.step(
            "MCP search failed",
            note="Stop before outfit generation and fit-card creation.",
        )
        return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )

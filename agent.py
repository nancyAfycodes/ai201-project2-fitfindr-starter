"""
agent.py

The FitFindr planning loop. Orchestrates all tools in response to a natural
language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import (
    search_listings,
    compare_prices,
    suggest_outfit,
    trend_awareness,
    create_fit_card,
    retry_with_fallback,
)


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "similar_items": [],
        "outfit_suggestion": None,
        "trend_info": None,
        "fit_card": None,
        "fallback_message": None,
        "error": None,
    }


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using regex patterns. Falls back gracefully if no match is found.

    Examples:
        "vintage graphic tee under $30, size M"
            → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
        "90s track jacket"
            → {"description": "90s track jacket", "size": None, "max_price": None}
    """
    # Extract price: "under $30", "max $45", "$30 or less", "no more than $60"
    price_match = re.search(
        r"(?:under|max|below|no more than|less than|up to)\s*\$?([\d]+(?:\.\d+)?)",
        query,
        re.IGNORECASE,
    )
    max_price = float(price_match.group(1)) if price_match else None

    # Extract size: "size M", "size 8", "in a M", "XL", "S/M"
    # Run on a version of the query with the price fragment removed to avoid
    # "$30" being captured as size "30".
    query_no_price = query
    if price_match:
        query_no_price = query[:price_match.start()] + query[price_match.end():]

    size_match = re.search(
        r"\b(?:size\s*)?([xX]{0,2}[sSlLmM]{1,2}(?:/[xX]{0,2}[sSlLmM]{1,2})?|"
        r"[Ww]\d{2}(?:\s*[Ll]\d{2})?|[Uu][Ss]\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)\b",
        query_no_price,
        re.IGNORECASE,
    )
    size = size_match.group(1).strip() if size_match else None

    # Description: strip price and size fragments, clean up punctuation
    desc = query
    if price_match:
        desc = desc[:price_match.start()] + desc[price_match.end():]
    if size_match:
        # also remove a preceding "size" word
        desc = re.sub(r"\bsize\b", "", desc, flags=re.IGNORECASE)
        desc = desc[:size_match.start()] + desc[size_match.end():]
    desc = re.sub(r"[,\s]+", " ", desc).strip(" ,.;")

    return {"description": desc, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop and returns
    the completed session dict.

    Planning loop logic:
        1. Parse query → extract description, size, max_price
        2. search_listings → if empty, trigger retry_with_fallback
           - fallback progressively loosens size then price then all filters
           - if still empty after fallback: set error, return early
        3. Select top result → store as selected_item
        4. Run compare_prices → find similar items in dataset
        5. Run suggest_outfit → Groq call with wardrobe context
        6. Run trend_awareness → Groq call for trend context
        7. Run create_fit_card → Groq call for caption
        8. Return completed session
    """
    session = _new_session(query, wardrobe)

    # ── Step 1: parse query ──────────────────────────────────────────────────
    parsed = _parse_query(query)
    session["parsed"] = parsed
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    # ── Step 2: search listings ──────────────────────────────────────────────
    results = search_listings(description, size=size, max_price=max_price)

    if not results:
        # Trigger retry with fallback
        fallback = retry_with_fallback(description, size=size, max_price=max_price)
        session["fallback_message"] = fallback["message"]
        results = fallback["results"]

        if not results:
            session["error"] = fallback["message"]
            return session

    session["search_results"] = results

    # ── Step 3: select top result ────────────────────────────────────────────
    session["selected_item"] = results[0]

    # ── Step 4: compare prices ───────────────────────────────────────────────
    session["similar_items"] = compare_prices(
        session["selected_item"],
        listings=results + session["search_results"],
    )

    # ── Step 5: suggest outfit ───────────────────────────────────────────────
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"],
        session["wardrobe"],
    )

    # ── Step 6: trend awareness ──────────────────────────────────────────────
    session["trend_info"] = trend_awareness(session["selected_item"])

    # ── Step 7: create fit card ──────────────────────────────────────────────
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"],
    )

    # ── Step 8: return completed session ────────────────────────────────────
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        item = session["selected_item"]
        print(f"Found: {item['title']} — ${item['price']} on {item['platform']}")
        if session["fallback_message"]:
            print(f"Note: {session['fallback_message']}")
        print(f"\nSimilar items: {len(session['similar_items'])} found")
        print(f"\nOutfit:\n{session['outfit_suggestion']}")
        print(f"\nTrends:\n{session['trend_info']}")
        print(f"\nFit card:\n{session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

    print("\n\n=== Empty wardrobe path ===\n")
    session3 = run_agent(
        query="vintage flannel shirt size XL",
        wardrobe=get_empty_wardrobe(),
    )
    if not session3["error"]:
        print(f"Found: {session3['selected_item']['title']}")
        print(f"\nOutfit (no wardrobe):\n{session3['outfit_suggestion']}")

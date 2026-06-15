"""
tools.py

All six FitFindr tools. Each tool is standalone and independently testable.

Tools:
    search_listings(description, size, max_price)       → list[dict]
    compare_prices(item, listings)                       → list[dict]
    suggest_outfit(new_item, wardrobe)                   → str
    trend_awareness(new_item)                            → str
    create_fit_card(outfit, new_item)                    → str
    retry_with_fallback(description, size, max_price)    → dict
"""

import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()

PRICE_BUFFER = 1.20  # compare_prices cap: 20% above original


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)


def _chat(prompt: str, temperature: float = 0.7) -> str:
    """Helper: single-turn Groq chat call. Returns response text."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching description,
    optional size, and optional price ceiling.

    Returns a list of matching listing dicts sorted by relevance (best first).
    Returns an empty list if nothing matches — does NOT raise.
    """
    try:
        listings = load_listings()
    except Exception as e:
        print(f"[search_listings] Failed to load listings: {e}")
        return []

    # Step 1: apply hard filters (price, size)
    candidates = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None:
            item_size = item["size"].lower()
            if size.lower() not in item_size:
                continue
        candidates.append(item)

    if not candidates:
        return []

    # Step 2: score by keyword overlap against description + style_tags + title
    keywords = set(description.lower().split())

    def _score(item: dict) -> int:
        haystack = " ".join([
            item["title"],
            item["description"],
            item["category"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
            item.get("brand") or "",
        ]).lower()
        return sum(1 for kw in keywords if kw in haystack)

    scored = [(item, _score(item)) for item in candidates]
    scored = [(item, score) for item, score in scored if score > 0]

    if not scored:
        return []

    scored.sort(key=lambda x: x[1], reverse=True)
    return [item for item, _ in scored]


# ── Tool 2: compare_prices ────────────────────────────────────────────────────

def compare_prices(
    item: dict,
    listings: list[dict] | None = None,
) -> list[dict]:
    """
    Find similar items within the dataset priced up to 20% above the given item.

    Args:
        item:     The selected listing dict.
        listings: Optional pre-loaded listings (avoids re-reading the file).

    Returns:
        A list of similar listing dicts (excluding the original), sorted by price.
        Returns an empty list if nothing comparable is found — does NOT raise.
    """
    try:
        all_listings = listings if listings is not None else load_listings()
    except Exception as e:
        print(f"[compare_prices] Failed to load listings: {e}")
        return []

    price_cap = item["price"] * PRICE_BUFFER
    item_tags = set(item["style_tags"])
    item_category = item["category"]

    similar = []
    for candidate in all_listings:
        if candidate["id"] == item["id"]:
            continue
        if candidate["category"] != item_category:
            continue
        if candidate["price"] > price_cap:
            continue
        # must share at least one style tag
        if not item_tags.intersection(set(candidate["style_tags"])):
            continue
        similar.append(candidate)

    similar.sort(key=lambda x: x["price"])
    return similar[:5]  # return top 5 similar items


# ── Tool 3: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Handles empty wardrobes gracefully by offering general styling advice.
    Returns a non-empty string — does NOT raise.
    """
    try:
        items = wardrobe.get("items", [])

        if not items:
            prompt = f"""You are a thrift fashion stylist. A user just found this secondhand item:

Item: {new_item['title']}
Description: {new_item['description']}
Style tags: {', '.join(new_item['style_tags'])}
Colors: {', '.join(new_item['colors'])}
Category: {new_item['category']}

They don't have a wardrobe on file yet. Give them 1–2 general outfit ideas — what kinds of pieces pair well with this item, what vibe it suits, and what to look for next. Keep it casual and specific, like advice from a stylish friend."""

        else:
            wardrobe_lines = "\n".join(
                f"- {w['name']} ({w['category']}, colors: {', '.join(w['colors'])}, tags: {', '.join(w['style_tags'])})"
                for w in items
            )
            prompt = f"""You are a thrift fashion stylist. A user just found this secondhand item:

Item: {new_item['title']}
Description: {new_item['description']}
Style tags: {', '.join(new_item['style_tags'])}
Colors: {', '.join(new_item['colors'])}
Category: {new_item['category']}

Their current wardrobe includes:
{wardrobe_lines}

Suggest 1–2 specific outfit combinations using the new item and named pieces from their wardrobe. Be specific about which wardrobe pieces to pair together. Keep it casual and specific, like advice from a stylish friend."""

        return _chat(prompt, temperature=0.7)

    except Exception as e:
        return (
            f"Outfit suggestions are unavailable right now ({e}). "
            "Try again in a moment, or check your API key."
        )


# ── Tool 4: trend_awareness ───────────────────────────────────────────────────

def trend_awareness(new_item: dict) -> str:
    """
    Generate trend context for a given item using the LLM.

    Returns a short paragraph on how the item fits current secondhand fashion
    trends. Does NOT scrape live sites — uses LLM knowledge.
    Returns a non-empty string — does NOT raise.
    """
    try:
        prompt = f"""You are a fashion trend analyst who specialises in secondhand and thrift style.

A user found this item:
Item: {new_item['title']}
Style tags: {', '.join(new_item['style_tags'])}
Colors: {', '.join(new_item['colors'])}
Category: {new_item['category']}

In 3–4 sentences, tell them how this item fits into current secondhand fashion trends. 
Mention specific aesthetics it aligns with (e.g. quiet luxury, dark academia, Y2K revival, gorpcore), 
what's popular on platforms like Depop and Poshmark right now, and one styling tip that's trending. 
Keep the tone conversational and enthusiastic."""

        return _chat(prompt, temperature=0.75)

    except Exception as e:
        return (
            f"Trend info is unavailable right now ({e}). "
            "The item still looks great — trust your instincts!"
        )


# ── Tool 5: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable Instagram/TikTok-style caption for the outfit.

    Guards against empty outfit input. Uses higher temperature for variety.
    Returns a non-empty string — does NOT raise.
    """
    if not outfit or not outfit.strip():
        return (
            "Couldn't generate a fit card — no outfit suggestion was available. "
            "Try refining your search or checking your wardrobe settings."
        )

    try:
        prompt = f"""You are writing an OOTD caption for a thrift fashion Instagram post.

The outfit:
{outfit}

The thrifted item:
- Name: {new_item['title']}
- Price: ${new_item['price']}
- Platform: {new_item['platform']}
- Condition: {new_item['condition']}

Write a 2–4 sentence caption that:
- Sounds casual and authentic, like a real OOTD post — not a product description
- Mentions the item name, price, and platform once each, naturally
- Captures the specific vibe of the outfit
- Ends with 3–5 relevant hashtags

Write only the caption — no intro, no explanation."""

        return _chat(prompt, temperature=0.95)

    except Exception as e:
        return (
            f"Fit card generation failed ({e}). "
            "Your outfit suggestion is still above — screenshot that!"
        )


# ── Tool 6: retry_with_fallback ───────────────────────────────────────────────

def retry_with_fallback(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> dict:
    """
    Called when search_listings returns nothing. Progressively loosens filters
    and retries, alerting the user to what was removed.

    Returns:
        {
            "results": list[dict],   # may be empty
            "message": str,          # explains what was changed / outcome
        }
    """
    attempts = []

    # Attempt 1: drop size filter
    if size is not None:
        results = search_listings(description, size=None, max_price=max_price)
        if results:
            return {
                "results": results,
                "message": (
                    f"No results found for size '{size}', so we removed the size filter. "
                    f"Here are the closest matches — check the listings for size details."
                ),
            }
        attempts.append("size filter")

    # Attempt 2: raise price cap by 25%
    if max_price is not None:
        relaxed_price = round(max_price * 1.25, 2)
        results = search_listings(description, size=None, max_price=relaxed_price)
        if results:
            return {
                "results": results,
                "message": (
                    f"No results matched your original filters, so we removed the size filter "
                    f"and raised the price cap from ${max_price} to ${relaxed_price}. "
                    f"Here's what we found."
                ),
            }
        attempts.append("price filter")

    # Attempt 3: description-only search (no filters at all)
    results = search_listings(description, size=None, max_price=None)
    if results:
        removed = " and ".join(attempts) if attempts else "all filters"
        return {
            "results": results,
            "message": (
                f"We broadened your search by removing {removed}. "
                f"Here are the closest description matches — prices and sizes may vary."
            ),
        }

    # All attempts failed
    return {
        "results": [],
        "message": (
            "We couldn't find anything matching your search, even after broadening the filters. "
            "Try a different description, size, or price range."
        ),
    }
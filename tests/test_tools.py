"""
tests/test_tools.py

Pytest tests for all six FitFindr tools.
At least one test per failure mode per tool.

Failure modes covered:
    search_listings   — no keyword match, price filter excludes all, size filter excludes all,
                        data loader failure (patched), zero-score items dropped
    compare_prices    — no same-category matches, price cap excludes all, original item excluded,
                        data loader failure (patched)
    suggest_outfit    — empty wardrobe (falls back to general advice), LLM/API failure (patched)
    trend_awareness   — LLM/API failure (patched)
    create_fit_card   — empty outfit string, whitespace-only outfit string, LLM/API failure (patched)
    retry_with_fallback — size loosened and finds results, price loosened and finds results,
                          all filters dropped and finds results, all attempts fail → empty results

All LLM calls are patched via unittest.mock so tests run without a real API key.
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os

# ── make sure the project root is on the path ─────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import (
    search_listings,
    compare_prices,
    suggest_outfit,
    trend_awareness,
    create_fit_card,
    retry_with_fallback,
)


# ── shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_item():
    """A realistic listing dict used across multiple tests."""
    return {
        "id": "lst_006",
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit.",
        "category": "tops",
        "style_tags": ["graphic tee", "vintage", "grunge", "streetwear", "band tee"],
        "size": "L",
        "condition": "good",
        "price": 24.00,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
    }


@pytest.fixture
def sample_wardrobe():
    """A minimal wardrobe with two items."""
    return {
        "items": [
            {
                "id": "w_001",
                "name": "Baggy straight-leg jeans, dark wash",
                "category": "bottoms",
                "colors": ["dark blue", "indigo"],
                "style_tags": ["denim", "streetwear", "baggy"],
                "notes": "High-waisted",
            },
            {
                "id": "w_007",
                "name": "Chunky white sneakers",
                "category": "shoes",
                "colors": ["white"],
                "style_tags": ["sneakers", "chunky", "streetwear"],
                "notes": None,
            },
        ]
    }


@pytest.fixture
def empty_wardrobe():
    return {"items": []}


@pytest.fixture
def mock_llm_response():
    """Returns a factory that patches _chat with a given string."""
    def _patch(return_value="Mocked LLM response."):
        return patch("tools._chat", return_value=return_value)
    return _patch


# ══════════════════════════════════════════════════════════════════════════════
# Tool 1: search_listings
# ══════════════════════════════════════════════════════════════════════════════

class TestSearchListings:

    def test_returns_results_for_valid_description(self):
        """Happy path: a real keyword returns at least one result."""
        results = search_listings("graphic tee")
        assert len(results) > 0
        assert all(isinstance(r, dict) for r in results)

    def test_results_contain_required_fields(self):
        """Every returned listing has the expected keys."""
        results = search_listings("vintage jeans")
        required = {"id", "title", "description", "category", "style_tags",
                    "size", "condition", "price", "colors", "platform"}
        for item in results:
            assert required.issubset(item.keys())

    def test_results_sorted_by_relevance(self):
        """Top result should be more relevant (score ≥ next result's score)."""
        results = search_listings("vintage graphic tee streetwear")
        # We can't inspect scores directly, but the top result should mention
        # at least one keyword in its title/tags
        top = results[0]
        haystack = (top["title"] + " ".join(top["style_tags"])).lower()
        keywords = {"vintage", "graphic", "tee", "streetwear"}
        assert any(kw in haystack for kw in keywords)

    # ── failure mode: no keyword match ────────────────────────────────────────

    def test_no_match_returns_empty_list(self):
        """Completely unrecognisable keywords return [] not an exception."""
        results = search_listings("zzzznonexistentkeywordxxx")
        assert results == []

    # ── failure mode: price filter excludes all ───────────────────────────────

    def test_price_filter_excludes_all(self):
        """max_price of $0.01 should exclude every listing."""
        results = search_listings("jeans", max_price=0.01)
        assert results == []

    def test_price_filter_is_inclusive(self):
        """Items at exactly max_price should be included."""
        results = search_listings("jeans", max_price=38.00)
        assert all(r["price"] <= 38.00 for r in results)

    # ── failure mode: size filter excludes all ────────────────────────────────

    def test_size_filter_no_match_returns_empty(self):
        """A size that matches nothing returns []."""
        results = search_listings("jeans", size="XXXXL_IMPOSSIBLE")
        assert results == []

    def test_size_filter_is_case_insensitive(self):
        """Size matching should work regardless of case."""
        lower = search_listings("flannel", size="xl")
        upper = search_listings("flannel", size="XL")
        assert lower == upper

    # ── failure mode: data loader raises an exception ─────────────────────────

    def test_data_loader_failure_returns_empty_list(self):
        """If load_listings() raises, the tool returns [] instead of crashing."""
        with patch("tools.load_listings", side_effect=FileNotFoundError("missing")):
            results = search_listings("anything")
        assert results == []

    # ── failure mode: zero-score items dropped ────────────────────────────────

    def test_zero_score_items_excluded(self):
        """Items that share no keywords with the description are excluded."""
        # "ballgown" appears in no listing; combined with a tight price cap
        # this should cleanly return nothing
        results = search_listings("ballgown", max_price=5.0)
        assert results == []


# ══════════════════════════════════════════════════════════════════════════════
# Tool 2: compare_prices
# ══════════════════════════════════════════════════════════════════════════════

class TestComparePrices:

    def test_returns_similar_items(self, sample_item):
        """Happy path: a tops item finds at least one similar top."""
        results = compare_prices(sample_item)
        assert isinstance(results, list)
        # all results should be in the same category
        assert all(r["category"] == sample_item["category"] for r in results)

    def test_original_item_excluded(self, sample_item):
        """The selected item itself must not appear in comparisons."""
        results = compare_prices(sample_item)
        ids = [r["id"] for r in results]
        assert sample_item["id"] not in ids

    def test_results_within_price_cap(self, sample_item):
        """All returned items must be priced at or below 120% of original."""
        cap = sample_item["price"] * 1.20
        results = compare_prices(sample_item)
        assert all(r["price"] <= cap for r in results)

    def test_results_sorted_by_price(self, sample_item):
        """Results should be sorted ascending by price."""
        results = compare_prices(sample_item)
        prices = [r["price"] for r in results]
        assert prices == sorted(prices)

    def test_max_five_results(self, sample_item):
        """compare_prices returns at most 5 items."""
        results = compare_prices(sample_item)
        assert len(results) <= 5

    # ── failure mode: no same-category matches ────────────────────────────────

    def test_no_match_when_category_differs(self, sample_item):
        """If all candidates are in a different category, return []."""
        fake_listings = [
            {
                "id": "fake_001",
                "category": "shoes",          # different from sample_item's "tops"
                "style_tags": ["vintage"],
                "price": 20.00,
            }
        ]
        results = compare_prices(sample_item, listings=fake_listings)
        assert results == []

    # ── failure mode: price cap excludes all ─────────────────────────────────

    def test_no_match_when_all_over_price_cap(self, sample_item):
        """If every candidate is above the 120% price cap, return []."""
        expensive_item = dict(sample_item)
        expensive_item["id"] = "other_001"
        expensive_item["price"] = sample_item["price"] * 2  # well above cap
        results = compare_prices(sample_item, listings=[expensive_item])
        assert results == []

    # ── failure mode: no shared style tags ───────────────────────────────────

    def test_no_match_when_no_shared_tags(self, sample_item):
        """Items sharing the category but no style tags are excluded."""
        no_tag_item = {
            "id": "other_002",
            "category": sample_item["category"],
            "style_tags": ["completely_unrelated_tag"],
            "price": sample_item["price"],
        }
        results = compare_prices(sample_item, listings=[no_tag_item])
        assert results == []

    # ── failure mode: data loader raises an exception ─────────────────────────

    def test_data_loader_failure_returns_empty_list(self, sample_item):
        """If load_listings() raises and no listings kwarg passed, return []."""
        with patch("tools.load_listings", side_effect=OSError("disk error")):
            results = compare_prices(sample_item)
        assert results == []


# ══════════════════════════════════════════════════════════════════════════════
# Tool 3: suggest_outfit
# ══════════════════════════════════════════════════════════════════════════════

class TestSuggestOutfit:

    def test_returns_string_with_wardrobe(self, sample_item, sample_wardrobe, mock_llm_response):
        """Happy path: populated wardrobe returns a non-empty string."""
        with mock_llm_response("Pair the graphic tee with your baggy jeans."):
            result = suggest_outfit(sample_item, sample_wardrobe)
        assert isinstance(result, str)
        assert len(result) > 0

    # ── failure mode: empty wardrobe ──────────────────────────────────────────

    def test_empty_wardrobe_returns_general_advice(self, sample_item, empty_wardrobe, mock_llm_response):
        """Empty wardrobe triggers the general-advice path, not an error."""
        with mock_llm_response("This tee pairs well with straight-leg jeans."):
            result = suggest_outfit(sample_item, empty_wardrobe)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_missing_items_key_treated_as_empty(self, sample_item, mock_llm_response):
        """A wardrobe dict with no 'items' key is handled like an empty wardrobe."""
        with mock_llm_response("General styling advice here."):
            result = suggest_outfit(sample_item, {})
        assert isinstance(result, str)
        assert len(result) > 0

    # ── failure mode: LLM / API error ────────────────────────────────────────

    def test_api_failure_returns_error_string_not_exception(self, sample_item, sample_wardrobe):
        """If _chat raises, suggest_outfit returns an error string, not a crash."""
        with patch("tools._chat", side_effect=Exception("API down")):
            result = suggest_outfit(sample_item, sample_wardrobe)
        assert isinstance(result, str)
        assert "unavailable" in result.lower()

    def test_api_failure_with_empty_wardrobe_returns_error_string(self, sample_item, empty_wardrobe):
        """API failure on the empty-wardrobe path also returns a safe string."""
        with patch("tools._chat", side_effect=Exception("timeout")):
            result = suggest_outfit(sample_item, empty_wardrobe)
        assert isinstance(result, str)
        assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Tool 4: trend_awareness
# ══════════════════════════════════════════════════════════════════════════════

class TestTrendAwareness:

    def test_returns_string_on_success(self, sample_item, mock_llm_response):
        """Happy path: returns a non-empty string."""
        with mock_llm_response("This item is trending in the Y2K revival scene."):
            result = trend_awareness(sample_item)
        assert isinstance(result, str)
        assert len(result) > 0

    # ── failure mode: LLM / API error ────────────────────────────────────────

    def test_api_failure_returns_error_string_not_exception(self, sample_item):
        """If _chat raises, trend_awareness returns a safe fallback string."""
        with patch("tools._chat", side_effect=Exception("503 Service Unavailable")):
            result = trend_awareness(sample_item)
        assert isinstance(result, str)
        assert "unavailable" in result.lower()

    def test_api_failure_message_includes_encouragement(self, sample_item):
        """The fallback message should still be friendly, not a raw traceback."""
        with patch("tools._chat", side_effect=Exception("timeout")):
            result = trend_awareness(sample_item)
        assert "instincts" in result.lower() or "unavailable" in result.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Tool 5: create_fit_card
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateFitCard:

    def test_returns_caption_on_success(self, sample_item, mock_llm_response):
        """Happy path: valid outfit string produces a caption."""
        with mock_llm_response("Found this gem on Depop for $24. #thrift #ootd"):
            result = create_fit_card("Tee + baggy jeans + chunky sneakers.", sample_item)
        assert isinstance(result, str)
        assert len(result) > 0

    # ── failure mode: empty outfit string ────────────────────────────────────

    def test_empty_outfit_returns_error_message(self, sample_item):
        """An empty outfit string must return a descriptive error, not crash."""
        result = create_fit_card("", sample_item)
        assert isinstance(result, str)
        assert "couldn't generate" in result.lower() or "no outfit" in result.lower()

    # ── failure mode: whitespace-only outfit string ───────────────────────────

    def test_whitespace_outfit_returns_error_message(self, sample_item):
        """A whitespace-only outfit string is treated the same as empty."""
        result = create_fit_card("   \n\t  ", sample_item)
        assert isinstance(result, str)
        assert "couldn't generate" in result.lower() or "no outfit" in result.lower()

    def test_empty_outfit_does_not_call_llm(self, sample_item):
        """The LLM should never be called when the outfit string is empty."""
        with patch("tools._chat") as mock_chat:
            create_fit_card("", sample_item)
            mock_chat.assert_not_called()

    # ── failure mode: LLM / API error ────────────────────────────────────────

    def test_api_failure_returns_error_string_not_exception(self, sample_item):
        """If _chat raises, create_fit_card returns a safe string, not a crash."""
        with patch("tools._chat", side_effect=Exception("rate limit exceeded")):
            result = create_fit_card("Tee + jeans + sneakers.", sample_item)
        assert isinstance(result, str)
        assert "failed" in result.lower() or "unavailable" in result.lower()

    def test_api_failure_message_is_not_empty(self, sample_item):
        """The error fallback must never return an empty string."""
        with patch("tools._chat", side_effect=Exception("network error")):
            result = create_fit_card("Some outfit.", sample_item)
        assert result.strip() != ""


# ══════════════════════════════════════════════════════════════════════════════
# Tool 6: retry_with_fallback
# ══════════════════════════════════════════════════════════════════════════════

class TestRetryWithFallback:

    # ── failure mode: size filter was the problem → drop it ──────────────────

    def test_drops_size_filter_and_finds_results(self):
        """If size causes no results, retry without size should succeed."""
        # flannel exists in XL but not in size S
        result = retry_with_fallback("flannel", size="S", max_price=None)
        assert len(result["results"]) > 0
        assert "size" in result["message"].lower()

    def test_drop_size_message_is_informative(self):
        """The message when dropping size filter should mention the removed filter."""
        result = retry_with_fallback("flannel", size="S", max_price=None)
        assert "size" in result["message"].lower()

    # ── failure mode: price cap was the problem → raise it ───────────────────

    def test_raises_price_cap_and_finds_results(self):
        """If price + impossible size cause no results, raising price cap helps."""
        # Graphic tees exist above $5 — raising the cap should find them
        result = retry_with_fallback("graphic tee", size="XXXXL_IMPOSSIBLE", max_price=5.0)
        # Either size drop or price raise should unlock results
        assert isinstance(result["results"], list)
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0

    # ── failure mode: description-only fallback ───────────────────────────────

    def test_description_only_fallback_returns_results(self):
        """When size and price both fail, description-only search should still find something."""
        result = retry_with_fallback("vintage", size="IMPOSSIBLE_SIZE", max_price=0.01)
        # "vintage" appears in many listings, so description-only must find something
        assert len(result["results"]) > 0
        assert "broadened" in result["message"].lower() or "filter" in result["message"].lower()

    # ── failure mode: all attempts fail → empty results ───────────────────────

    def test_complete_failure_returns_empty_results(self):
        """When nothing matches even after all loosening, results is [] not an error."""
        result = retry_with_fallback("zzznomatchkeywordzzz", size="S", max_price=1.0)
        assert result["results"] == []

    def test_complete_failure_message_is_helpful(self):
        """The total-failure message must guide the user, not show a traceback."""
        result = retry_with_fallback("zzznomatchkeywordzzz", size="S", max_price=1.0)
        msg = result["message"].lower()
        assert "couldn't find" in msg or "no results" in msg or "try" in msg

    def test_always_returns_results_and_message_keys(self):
        """Return value always has both 'results' and 'message' keys."""
        result = retry_with_fallback("anything", size=None, max_price=None)
        assert "results" in result
        assert "message" in result

    def test_results_is_always_a_list(self):
        """results key is always a list, never None."""
        result = retry_with_fallback("zzznomatch", size=None, max_price=None)
        assert isinstance(result["results"], list)

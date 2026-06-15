"""
Utility functions for loading the mock listings dataset and wardrobe schema.
"""

import json
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_listings() -> list[dict]:
    path = os.path.join(_DATA_DIR, "listings.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_wardrobe_schema() -> dict:
    path = os.path.join(_DATA_DIR, "wardrobe_schema.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_example_wardrobe() -> dict:
    return load_wardrobe_schema()["example_wardrobe"]


def get_empty_wardrobe() -> dict:
    return load_wardrobe_schema()["empty_wardrobe"]


if __name__ == "__main__":
    listings = load_listings()
    print(f"Loaded {len(listings)} listings.")
    print(f"First listing: {listings[0]['title']} — ${listings[0]['price']}")
    wardrobe = get_example_wardrobe()
    print(f"\nExample wardrobe has {len(wardrobe['items'])} items.")
    print(f"First item: {wardrobe['items'][0]['name']}")

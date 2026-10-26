# tests/factories.py
# Small helpers to build test data without touching the network

from itertools import count

from src.scrapers.base_scraper import RawProduct
from src.transformers.cleaner import CleanProduct

_ids = count(1)


def make_raw(**overrides) -> RawProduct:
    """Builds a RawProduct with sensible defaults."""
    n = next(_ids)
    data = {
        "source": "vinted",
        "url": f"https://www.vinted.fr/items/{n}-robe",
        "title": f"Robe test {n}",
        "price_raw": "25.00",
        "category_raw": "women dresses",
        "brand": "zara",
    }
    data.update(overrides)
    return RawProduct(**data)


def make_clean(**overrides) -> CleanProduct:
    """Builds a CleanProduct with sensible defaults."""
    n = next(_ids)
    data = {
        "source": "vinted",
        "url": f"https://www.vinted.fr/items/{n}-robe",
        "slug": f"vinted-robe-{n}",
        "title": f"Robe {n}",
        "brand": "Zara",
        "price": 25.0,
        "price_original": None,
        "currency": "EUR",
        "category": "women_dresses",
        "category_raw": "women dresses",
        "image_url": "",
    }
    data.update(overrides)
    return CleanProduct(**data)

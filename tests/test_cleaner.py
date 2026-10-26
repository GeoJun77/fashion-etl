# tests/test_cleaner.py
# Unit tests for the Cleaner : price parsing, URL normalization, deduplication

from datetime import timezone

import pytest

from src.transformers.cleaner import Cleaner, parse_price
from tests.factories import make_raw


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("29.99", 29.99),
        ("29,99 €", 29.99),
        ("1 299,00 €", 1299.0),
        ("1 299,00 €", 1299.0),   # narrow no-break space, as written by French sites
        ("1.299,00", 1299.0),
        ("1,299.00", 1299.0),
        ("1.299", 1299.0),
        ("100.0000", 100.0),                  # Awin feeds use 4 decimals
        ("EUR100.00", 100.0),
        ("29,99 39,99", 29.99),               # only the first price is read
        (12.5, 12.5),
        ("", None),
        ("gratuit", None),
        (None, None),
    ],
)
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


def test_price_outside_range_becomes_null():
    clean = Cleaner().clean([make_raw(price_raw="0.10"), make_raw(price_raw="25000")])
    assert [p.price for p in clean] == [None, None]


def test_original_price_kept_for_promotions():
    raw = make_raw(price_raw="30", extra={"has_promo": True, "promo_price": "45,00"})
    product = Cleaner().clean([raw])[0]
    assert product.is_promotional is True
    assert product.price_original == 45.0


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://Sneakin.fr/m18209-adidas?variant=31239", "https://sneakin.fr/m18209-adidas"),
        ("https://shop.fr/p/12/?utm_source=x&utm_medium=y", "https://shop.fr/p/12"),
        # Identifying parameters must be kept, or different products would be merged
        ("https://shop.fr/product.php?id=12&ref=abc", "https://shop.fr/product.php?id=12"),
        ("https://www.awin1.com/pclick.php?p=44361667192&a=1", "https://www.awin1.com/pclick.php?p=44361667192&a=1"),
    ],
)
def test_normalize_url(url, expected):
    assert Cleaner.normalize_url(url) == expected


def test_deduplicates_size_variants():
    raws = [
        make_raw(url="https://sneakin.fr/m1-sneaker?variant=1"),
        make_raw(url="https://sneakin.fr/m1-sneaker?variant=2"),
        make_raw(url="https://sneakin.fr/m2-sneaker?variant=1"),
    ]
    cleaner = Cleaner()
    clean = cleaner.clean(raws)
    assert len(clean) == 2
    assert cleaner.stats["duplicates"] == 1


def test_products_with_query_ids_are_not_merged():
    """Regression : URLs used to be cut at '?', which merged every Awin product into one."""
    raws = [make_raw(url=f"https://www.awin1.com/pclick.php?p={i}") for i in range(5)]
    assert len(Cleaner().clean(raws)) == 5


def test_empty_title_is_dropped():
    cleaner = Cleaner()
    assert cleaner.clean([make_raw(title="   ")]) == []
    assert cleaner.stats["empty_title"] == 1


def test_normalizes_fields():
    raw = make_raw(
        title="  Robe   midi  ",
        brand="  ba&sh ",
        colors=["Noir", " noir", "Bleu "],
        sizes=["M", " ", "L"],
        category_raw="Femmes > Vêtements > Robes > Robes midi",
    )
    p = Cleaner().clean([raw])[0]
    assert p.title == "Robe midi"
    assert p.brand == "Ba&Sh"
    assert p.colors == ["bleu", "noir"]
    assert p.sizes == ["M", "L"]
    assert p.category == "women_dresses"
    assert p.slug == "vinted-robe-midi"
    assert p.scraped_at.tzinfo == timezone.utc

# tests/test_scrapers.py
# Parsing tests for the real sources, on small hand-made inputs (no network)

import io
import zipfile

import pandas as pd

from src.scrapers.awin_scraper import AwinScraper
from src.scrapers.mock_scraper import MockScraper
from src.scrapers.vinted_scraper import VintedScraper

AWIN_COLUMNS = [
    "merchant_id", "product_name", "merchant_deep_link", "aw_deep_link", "search_price",
    "store_price", "rrp_price", "product_price_old", "brand_name", "merchant_category",
    "merchant_product_category_path", "merchant_image_url", "colour", "currency",
]


def _awin_row(**values) -> dict:
    row = dict.fromkeys(AWIN_COLUMNS, "")
    row.update(currency="EUR", **values)
    return row


def _feed_zip(rows: list[dict], path) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("feed.csv", pd.DataFrame(rows).to_csv(sep=";", index=False))
    path.write_bytes(buffer.getvalue())
    return str(path)


def _sneakin(i: int, variant: int = 1, category: str = "Lifestyle > T-shirt > Adulte > Homme") -> dict:
    return _awin_row(
        merchant_id="53373", product_name=f"T-shirt {i}",
        merchant_deep_link=f"https://sneakin.fr/m{i}-tshirt?variant={variant}",
        search_price="20.00", rrp_price="25.0000", brand_name="Nike",
        merchant_category=category, colour="Noir",
    )


def _kastner(i: int) -> dict:
    return _awin_row(
        merchant_id="121590", product_name=f"BRAX Jean {i} | 32/L30",
        merchant_deep_link=f"https://www.kastner-oehler.fr/brax-jean-{i}.html?article-size=32&feed",
        search_price="99.95", product_price_old="99.95", brand_name="BRAX",
        merchant_product_category_path="Hommes > Vêtements > Jeans > Slim,Boutique > Jeans",
    )


def test_awin_parses_both_merchants(tmp_path):
    feed = _feed_zip([_sneakin(1), _kastner(1)], tmp_path / "feed.zip")
    products = AwinScraper(feed_url=feed).run(max_products=10)

    sneakin, kastner = sorted(products, key=lambda p: p.source, reverse=True)
    assert sneakin.source == "sneakin"
    assert sneakin.url == "https://sneakin.fr/m1-tshirt"           # canonical URL, no variant
    assert sneakin.extra["has_promo"] is True                       # 20 < 25 (rrp_price)
    assert sneakin.extra["promo_price"] == 25.0

    assert kastner.source == "kastner_ohler"
    assert kastner.title == "BRAX Jean 1"                           # size suffix removed
    assert kastner.category_raw == "Hommes > Vêtements > Jeans > Slim"
    assert kastner.extra["has_promo"] is False                      # same price as before


def test_awin_skips_home_goods(tmp_path):
    row = _kastner(1)
    row["merchant_product_category_path"] = "Maison > Cuisine > Couteaux"
    feed = _feed_zip([row, _kastner(2)], tmp_path / "feed.zip")
    assert [p.title for p in AwinScraper(feed_url=feed).run(max_products=10)] == ["BRAX Jean 2"]


def test_awin_collapses_size_variants(tmp_path):
    feed = _feed_zip([_sneakin(1, variant=v) for v in range(5)], tmp_path / "feed.zip")
    assert len(AwinScraper(feed_url=feed).run(max_products=10)) == 1


def test_awin_quota_is_per_merchant(tmp_path):
    """The feed lists all Sneakin rows first : Kastner must still get its share."""
    rows = [_sneakin(i, category=f"Lifestyle > Cat{i % 10} > Adulte > Homme") for i in range(50)]
    rows += [_kastner(i) for i in range(5)]
    products = AwinScraper(feed_url=_feed_zip(rows, tmp_path / "feed.zip")).run(max_products=5)

    sources = [p.source for p in products]
    assert sources.count("sneakin") == 5
    assert sources.count("kastner_ohler") == 5


def test_vinted_parse_item():
    scraper = VintedScraper.__new__(VintedScraper)   # skip the network call of __init__
    item = {
        "id": 123, "title": "Robe fleurie", "path": "/items/123-robe-fleurie",
        "price": {"amount": "12.0", "currency_code": "EUR"},
        "brand_title": "Zara", "photo": {"url": "https://img/1.jpg"}, "size_title": "M",
    }
    product = scraper._parse_item(item, "women dresses")
    assert product.url == "https://www.vinted.fr/items/123-robe-fleurie"
    assert product.price_raw == "12.0"
    assert product.is_secondhand is True
    assert product.sizes == ["M"]


def test_mock_sources_are_clearly_fake():
    products = MockScraper().run(max_products=30)
    assert len(products) == 30
    assert all(p.source.startswith("mock_") for p in products)
    assert all(p.url.startswith("https://mock.example/") for p in products)

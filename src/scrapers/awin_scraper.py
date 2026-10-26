# src/scrapers/awin_scraper.py
# Scraper for Awin product feeds — downloads and parses CSV product feeds

import io
import zipfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests
from loguru import logger

from config.settings import settings
from src.scrapers.base_scraper import BaseScraper, RawProduct
from src.transformers.categories import normalize_category


def _clean(value) -> str:
    """Returns a stripped string, or "" for missing values (NaN / None)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class AwinScraper(BaseScraper):
    """
    Downloads and parses an Awin product feed (CSV inside a ZIP, ";" delimited).
    Supports Sneakin FR and Kastner & Öhler FR.

    - The feed is read in chunks to keep memory low (the CSV is ~1 GB).
    - Each merchant gets its own quota, so one big merchant cannot fill the whole run.
    - A per-category cap keeps the sample diverse (the feed is sorted by category,
      so reading the first N rows would only return T-shirts).
    - Feed rows are size variants: they are collapsed into one product via the
      canonical merchant URL (query string removed).
    """

    # Merchant IDs to source name mapping
    MERCHANT_MAP = {
        "53373":  "sneakin",
        "121590": "kastner_ohler",
    }

    # Kastner & Öhler also sells home goods and perfume : not fashion, skipped at extraction
    EXCLUDED_CATEGORY_LEVELS = {"maison", "cadeaux", "maison et art de vivre", "beauté"}

    CHUNK_SIZE = 5000            # rows read at a time
    CATEGORY_CAP_RATIO = 0.05    # max share of a merchant quota for one category

    def __init__(self, feed_url: str):
        super().__init__("awin")
        self.feed_url = feed_url

    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """Reads the feed and yields up to `max_products` products per merchant."""
        content = self._load_feed()
        if not content:
            raise RuntimeError("Awin feed could not be loaded")

        quota = {source: max_products for source in self.MERCHANT_MAP.values()}
        category_cap = max(5, int(max_products * self.CATEGORY_CAP_RATIO))
        per_category: Counter = Counter()
        seen_urls: set[str] = set()

        for chunk in self._read_chunks(content):
            for row in chunk.to_dict("records"):
                product = self._parse_row(row)
                if product is None or product.url in seen_urls:
                    continue
                if quota.get(product.source, 0) <= 0:
                    continue
                key = (product.source, normalize_category(product.category_raw, product.title))
                if per_category[key] >= category_cap:
                    continue

                seen_urls.add(product.url)
                per_category[key] += 1
                quota[product.source] -= 1
                yield product

            if all(left <= 0 for left in quota.values()):
                return

    def run(self, max_products: int | None = None) -> list[RawProduct]:
        """The limit applies per merchant here, not to the whole feed."""
        limit = max_products or settings.max_products
        logger.info(f"[awin] Starting feed parsing (max={limit} per merchant)")
        products = list(self.scrape(limit))
        by_source = Counter(p.source for p in products)
        logger.info(f"[awin] Done : {len(products)} products {dict(by_source)}")
        return products

    # --- Feed loading ---

    def _load_feed(self) -> bytes | None:
        """Loads the ZIP feed from a local path or downloads it from the URL."""
        local = Path(self.feed_url)
        if not self.feed_url.startswith(("http://", "https://")) and local.exists():
            logger.info(f"[Awin] Reading local feed {local}")
            return local.read_bytes()

        logger.info("[Awin] Downloading product feed...")
        try:
            response = requests.get(
                self.feed_url,
                timeout=300,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            logger.info(f"[Awin] Feed downloaded ({len(response.content) / 1024 / 1024:.1f} MB)")
            return response.content
        except requests.RequestException as e:
            logger.error(f"[Awin] Download failed : {e}")
            return None

    def _read_chunks(self, content: bytes) -> Iterator[pd.DataFrame]:
        """Reads the CSV inside the ZIP file in chunks to save memory."""
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            csv_filename = next(f for f in z.namelist() if f.endswith(".csv"))
            with z.open(csv_filename) as f:
                yield from pd.read_csv(
                    f,
                    sep=";",
                    encoding="utf-8",
                    on_bad_lines="skip",
                    chunksize=self.CHUNK_SIZE,
                    dtype=str,
                )

    # --- Row parsing ---

    @staticmethod
    def _canonical_url(url: str) -> str:
        """Removes the query string (size variant, tracking) from a merchant URL."""
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    def _parse_row(self, row: dict) -> RawProduct | None:
        """Parses a single CSV row into a RawProduct."""
        source = self.MERCHANT_MAP.get(_clean(row.get("merchant_id")))
        if source is None:
            return None

        title = _clean(row.get("product_name"))
        merchant_url = _clean(row.get("merchant_deep_link"))
        if not title or not merchant_url:
            return None

        # Kastner & Öhler appends the size to the title : "... blanc | M"
        if " | " in title:
            title = title.rsplit(" | ", 1)[0]

        price_raw = _clean(row.get("store_price")) or _clean(row.get("search_price"))

        # Sneakin uses merchant_category, Kastner & Öhler uses the category path
        category_raw = (
            _clean(row.get("merchant_category"))
            or _clean(row.get("merchant_product_category_path")).split(",")[0]
            or _clean(row.get("category_name"))
        )

        levels = {level.strip().lower() for level in category_raw.split(">")}
        if levels & self.EXCLUDED_CATEGORY_LEVELS:
            return None

        image_url = _clean(row.get("merchant_image_url")) or _clean(row.get("aw_image_url"))

        colour = _clean(row.get("colour"))
        colors = [c.strip() for c in colour.split(",") if c.strip()]
        size = _clean(row.get("Fashion:size"))
        sizes = [s.strip() for s in size.split(",") if s.strip()]

        # Promotion : the reference price is rrp_price (Sneakin) or product_price_old (K&Ö)
        price = _to_float(price_raw)
        reference = _to_float(_clean(row.get("rrp_price"))) or _to_float(_clean(row.get("product_price_old")))
        is_promo = bool(price and reference and price < reference)

        description = _clean(row.get("product_short_description")) or _clean(row.get("description"))[:500]

        return RawProduct(
            source=source,
            url=self._canonical_url(merchant_url),
            title=title,
            price_raw=price_raw,
            currency=_clean(row.get("currency")) or "EUR",
            category_raw=category_raw,
            brand=_clean(row.get("brand_name")),
            image_url=image_url,
            colors=colors,
            sizes=sizes,
            is_secondhand=False,
            extra={
                "has_promo":     is_promo,
                "promo_price":   reference if is_promo else None,  # original price before discount
                "material":      _clean(row.get("Fashion:material")),
                "description":   description,
                "affiliate_url": _clean(row.get("aw_deep_link")),
                "in_stock":      _clean(row.get("in_stock")),
            },
        )

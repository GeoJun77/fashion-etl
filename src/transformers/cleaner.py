# src/transformers/cleaner.py
# Cleans and normalizes raw products before loading into the database

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from loguru import logger

from config.settings import settings
from src.scrapers.base_scraper import RawProduct
from src.transformers.categories import normalize_category


@dataclass
class CleanProduct:
    """Represents a cleaned and normalized product, ready for the database."""
    source: str
    url: str
    slug: str
    title: str
    brand: str
    price: float | None
    price_original: float | None
    currency: str
    category: str
    category_raw: str
    image_url: str
    colors: list = field(default_factory=list)
    sizes: list = field(default_factory=list)
    is_promotional: bool = False
    is_secondhand: bool = False
    material: str = ""
    description: str = ""
    season: str = ""
    trend_keywords: list = field(default_factory=list)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Query parameters that never identify a product (tracking, size variants)
IGNORED_QUERY_PARAMS = {"variant", "article-size", "feed", "ref", "gclid", "fbclid"}

# First price-like token in a string : "1 299,00 €" -> "1 299,00"
# Either digits grouped by thousands ("1 299", "1.299.000") or a plain number ("29.99")
PRICE_TOKEN = re.compile(
    r"\d{1,3}(?:[ .,'\u00a0\u202f]\d{3}(?!\d))+(?:[.,]\d{1,4})?"
    r"|\d+(?:[.,]\d{1,4})?"
)


def parse_price(raw: str | float | None) -> float | None:
    """
    Parses a price written in any common format. Returns None if no number is found.

        "29.99"       -> 29.99        "29,99 €"   -> 29.99
        "1 299,00 €"  -> 1299.0       "1.299,00"  -> 1299.0
        "1,299.00"    -> 1299.0       "1.299"     -> 1299.0
        "100.0000"    -> 100.0
    """
    if raw is None:
        return None
    match = PRICE_TOKEN.search(str(raw))
    if not match:
        return None

    number = re.sub(r"[\s'\u00a0\u202f]", "", match.group()).rstrip(".,")
    has_dot, has_comma = "." in number, "," in number

    if has_dot and has_comma:
        # The last separator is the decimal one : "1.299,00" or "1,299.00"
        decimal = "," if number.rfind(",") > number.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        number = number.replace(thousands, "").replace(decimal, ".")
    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        integer, _, decimals = number.rpartition(sep)
        if number.count(sep) > 1 or len(decimals) == 3:
            # "1.299.000" or "1.299" -> thousands separator
            number = number.replace(sep, "")
        else:
            number = number.replace(sep, ".")

    try:
        return float(number)
    except ValueError:
        return None


class Cleaner:
    """
    Cleans and normalizes a list of RawProduct.
    Returns valid, deduplicated CleanProduct objects.
    """

    def __init__(self):
        self._stats = {
            "input": 0,
            "output": 0,
            "duplicates": 0,
            "invalid_price": 0,
            "empty_title": 0,
            "uncategorized": 0,
        }

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    def clean(self, raw_products: list[RawProduct]) -> list[CleanProduct]:
        """
        Cleans a list of raw products.
        Returns only valid and deduplicated products.
        """
        self._stats["input"] = len(raw_products)
        seen_urls: set[str] = set()
        cleaned: list[CleanProduct] = []

        for raw in raw_products:
            product = self._clean_one(raw)
            if product is None:
                continue

            # Deduplicate on the normalized URL
            if product.url in seen_urls:
                self._stats["duplicates"] += 1
                continue
            seen_urls.add(product.url)
            cleaned.append(product)

        self._stats["output"] = len(cleaned)
        self._log_stats()
        return cleaned

    def _clean_one(self, raw: RawProduct) -> CleanProduct | None:
        """Cleans a single raw product. Returns None if invalid."""
        title = self._clean_title(raw.title)
        if not title:
            self._stats["empty_title"] += 1
            return None

        # Prices outside the valid range are kept as NULL (and measured by the quality checks)
        price = self._valid_price(parse_price(raw.price_raw))
        if price is None:
            self._stats["invalid_price"] += 1

        # Original price, when the product is on sale
        is_promo = bool(raw.extra.get("has_promo", False))
        price_original = self._valid_price(parse_price(raw.extra.get("promo_price"))) if is_promo else None

        category = normalize_category(raw.category_raw, title)
        if category == "other":
            self._stats["uncategorized"] += 1

        return CleanProduct(
            source=raw.source,
            url=self.normalize_url(raw.url),
            slug=self.make_slug(f"{raw.source}-{title}"),
            title=title,
            brand=" ".join(raw.brand.split()).title() if raw.brand else "",
            price=price,
            price_original=price_original,
            currency=(raw.currency or "EUR").upper(),
            category=category,
            category_raw=raw.category_raw,
            image_url=raw.image_url,
            colors=sorted({c.strip().lower() for c in raw.colors if c.strip()}),
            sizes=[s.strip() for s in raw.sizes if s and s.strip()],
            is_promotional=is_promo,
            is_secondhand=raw.is_secondhand,
            material=raw.extra.get("material", "") or "",
            description=raw.extra.get("description", "") or "",
            season=raw.extra.get("season", "") or "",
            trend_keywords=raw.extra.get("trend_keywords", []) or [],
            scraped_at=raw.scraped_at,
        )

    # --- Helpers ---

    @staticmethod
    def _valid_price(price: float | None) -> float | None:
        if price is None or not (settings.min_price <= price <= settings.max_price):
            return None
        return round(price, 2)

    @staticmethod
    def _clean_title(raw: str) -> str:
        """Normalizes a product title."""
        if not raw:
            return ""
        return " ".join(raw.split())[:500]  # Collapse whitespace, limit length

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalizes a URL for deduplication : lowercase host, no trailing slash,
        no fragment, no tracking / variant query parameters.
        Other query parameters are kept — they may identify the product.
        """
        parts = urlsplit(url.strip())
        query = [
            (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in IGNORED_QUERY_PARAMS and not k.lower().startswith("utm_")
        ]
        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query),
            "",
        ))

    @staticmethod
    def make_slug(text: str) -> str:
        """Generates a URL-safe slug from any text."""
        nfkd = unicodedata.normalize("NFKD", text.lower())
        ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^\w\s-]", "", ascii_str)
        slug = re.sub(r"[-\s_]+", "-", slug).strip("-")
        return slug[:200]

    def _log_stats(self) -> None:
        """Logs cleaning statistics."""
        s = self._stats
        logger.info(
            f"[Cleaner] {s['input']} raw → {s['output']} clean | "
            f"duplicates={s['duplicates']} "
            f"invalid_price={s['invalid_price']} "
            f"empty_title={s['empty_title']} "
            f"uncategorized={s['uncategorized']}"
        )

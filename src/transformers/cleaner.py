# src/transformers/cleaner.py
# Cleans and normalizes raw products before loading into the database

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger

from src.scrapers.base_scraper import RawProduct


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
    scraped_at: datetime = field(default_factory=datetime.utcnow)


# Maps raw category labels to normalized categories
CATEGORY_MAP = {
    "women dresses":  "women_dresses",
    "women tops":     "women_tops",
    "women jeans":    "women_jeans",
    "women coats":    "women_coats",
    "women sneakers": "women_sneakers",
    "women bags":     "women_bags",
    "women skirts":   "women_skirts",
    "women blouses":  "women_blouses",
    "women knitwear": "women_knitwear",
    "women blazers":  "women_blazers",
    "women heels":    "women_heels",
    "women boots":    "women_boots",
    "women sandals":  "women_sandals",
    "women jewelry":  "women_jewelry",
    "women shorts":   "women_shorts",
    "women trousers": "women_trousers",
    "men t-shirts":   "men_tshirts",
    "men jeans":      "men_jeans",
    "men sneakers":   "men_sneakers",
    "men coats":      "men_coats",
    "men shirts":     "men_shirts",
    "men knitwear":   "men_knitwear",
    "men blazers":    "men_blazers",
    "men trousers":   "men_trousers",
    "men boots":      "men_boots",
    "men bags":       "men_bags",
    "men shorts":     "men_shorts",
    "girls dresses":  "girls_dresses",
    "girls tops":     "girls_tops",
    "girls jeans":    "girls_jeans",
    "girls coats":    "girls_coats",
    "girls sneakers": "girls_sneakers",
    "girls skirts":   "girls_skirts",
    "girls boots":    "girls_boots",
    "boys t-shirts":  "boys_tshirts",
    "boys shirts":    "boys_shirts",
    "boys jeans":     "boys_jeans",
    "boys coats":     "boys_coats",
    "boys sneakers":  "boys_sneakers",
    "boys shorts":    "boys_shorts",
}


class Cleaner:
    """
    Cleans and normalizes a list of RawProduct.
    Returns valid, deduplicated CleanProduct objects.
    """

    # Extracts a numeric price from any string
    PRICE_PATTERN = re.compile(r"(\d+[.,]?\d*)")

    def __init__(self):
        self._stats = {
            "input": 0,
            "output": 0,
            "duplicates": 0,
            "invalid_price": 0,
            "empty_title": 0,
        }

    def clean(self, raw_products: list[RawProduct]) -> list[CleanProduct]:
        """
        Cleans a list of raw products.
        Returns only valid and deduplicated products.
        """
        self._stats["input"] = len(raw_products)
        seen_urls: set[str] = set()
        cleaned: list[CleanProduct] = []

        for raw in raw_products:
            # Deduplicate by normalized URL
            norm_url = self._normalize_url(raw.url)
            if norm_url in seen_urls:
                self._stats["duplicates"] += 1
                continue
            seen_urls.add(norm_url)

            product = self._clean_one(raw)
            if product:
                cleaned.append(product)

        self._stats["output"] = len(cleaned)
        self._log_stats()
        return cleaned

    def _clean_one(self, raw: RawProduct) -> CleanProduct | None:
        """Cleans a single raw product. Returns None if invalid."""
        # Clean title
        title = self._clean_title(raw.title)
        if not title:
            self._stats["empty_title"] += 1
            return None

        # Extract price
        price = self._parse_price(raw.price_raw)
        if price is None:
            self._stats["invalid_price"] += 1

        # Extract original price if on sale
        price_original = None
        if raw.extra.get("has_promo") and raw.extra.get("promo_price"):
            price_original = self._parse_price(str(raw.extra["promo_price"]))

        # Normalize category
        category = CATEGORY_MAP.get(raw.category_raw, "other")

        # Generate unique slug
        slug = self._make_slug(f"{raw.source}-{title}")

        # Check if promotional
        is_promo = bool(raw.extra.get("has_promo", False))

        return CleanProduct(
            source=raw.source,
            url=raw.url,
            slug=slug,
            title=title,
            brand=raw.brand.strip().title() if raw.brand else "",
            price=price,
            price_original=price_original,
            currency=raw.currency,
            category=category,
            category_raw=raw.category_raw,
            image_url=raw.image_url,
            colors=[c.strip().lower() for c in raw.colors if c.strip()],
            sizes=raw.sizes,
            is_promotional=is_promo,
            is_secondhand=raw.is_secondhand,
            material=raw.extra.get("material", ""),
            description=raw.extra.get("description", ""),
            season=raw.extra.get("season", ""),
            trend_keywords=raw.extra.get("trend_keywords", []),
            scraped_at=raw.scraped_at,
        )

    # --- Private helpers ---

    def _clean_title(self, raw: str) -> str:
        """Normalizes a product title."""
        if not raw:
            return ""
        title = raw.strip()
        title = " ".join(title.split())  # Collapse multiple spaces
        return title[:500]              # Limit length

    def _parse_price(self, raw: str) -> float | None:
        """Parses a price from any string format. Returns None if invalid."""
        if not raw:
            return None
        raw = raw.replace("\u00a0", " ").strip()
        match = self.PRICE_PATTERN.search(raw)
        if not match:
            return None
        try:
            price = float(match.group(1).replace(",", "."))
            # Validate price range
            if 0.5 <= price <= 9999.0:
                return round(price, 2)
            return None
        except (ValueError, TypeError):
            return None

    def _normalize_url(self, url: str) -> str:
        """Normalizes a URL for deduplication — removes query params."""
        return url.split("?")[0].rstrip("/").lower()

    @staticmethod
    def _make_slug(text: str) -> str:
        """Generates a URL-safe slug from any text."""
        # Decompose accented characters
        nfkd = unicodedata.normalize("NFKD", text.lower())
        ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^\w\s-]", "", ascii_str)
        slug = re.sub(r"[-\s]+", "-", slug).strip("-")
        return slug[:200]

    def _log_stats(self) -> None:
        """Logs cleaning statistics."""
        s = self._stats
        logger.info(
            f"[Cleaner] {s['input']} raw → {s['output']} clean | "
            f"duplicates={s['duplicates']} "
            f"invalid_price={s['invalid_price']} "
            f"empty_title={s['empty_title']}"
        )
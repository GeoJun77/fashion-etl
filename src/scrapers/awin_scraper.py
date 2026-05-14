# src/scrapers/awin_scraper.py
# Scraper for Awin product feeds — downloads and parses CSV product feeds

import io
import zipfile
from typing import Iterator

import pandas as pd
import requests
from loguru import logger

from src.scrapers.base_scraper import BaseScraper, RawProduct


class AwinScraper(BaseScraper):
    """
    Downloads and parses Awin product feed CSV files.
    Supports Kastner & Ohler FR and Sneakin FR feeds.
    Feed format : CSV compressed as ZIP, semicolon delimited.
    Reads the feed in chunks to avoid memory issues.
    """

    # Merchant IDs to source name mapping
    MERCHANT_MAP = {
        "53373":  "sneakin",
        "121590": "kastner_ohler",
    }

    CHUNK_SIZE = 1000  # Number of rows to read at a time

    def __init__(self, feed_url: str):
        super().__init__("awin")
        self.feed_url = feed_url

    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """Downloads the feed and parses products chunk by chunk."""
        logger.info("[Awin] Downloading product feed...")

        content = self._download_zip()
        if not content:
            logger.error("[Awin] Failed to download feed")
            return

        count = 0
        for chunk in self._read_chunks(content):
            for _, row in chunk.iterrows():
                if count >= max_products:
                    return
                product = self._parse_row(row)
                if product:
                    yield product
                    count += 1

    def _download_zip(self) -> bytes | None:
        """Downloads the ZIP feed and returns raw bytes."""
        try:
            response = requests.get(
                self.feed_url,
                timeout=120,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            logger.info(f"[Awin] Feed downloaded ({len(response.content) / 1024 / 1024:.1f} MB)")
            return response.content

        except Exception as e:
            logger.error(f"[Awin] Download failed : {e}")
            return None

    def _read_chunks(self, content: bytes) -> Iterator[pd.DataFrame]:
        """Reads the CSV inside the ZIP file in chunks to save memory."""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                csv_filename = [f for f in z.namelist() if f.endswith(".csv")][0]
                with z.open(csv_filename) as f:
                    chunks = pd.read_csv(
                        f,
                        sep=";",
                        encoding="utf-8",
                        on_bad_lines="skip",
                        low_memory=True,
                        chunksize=self.CHUNK_SIZE,
                        dtype=str,  # Read everything as string to avoid memory issues
                    )
                    for chunk in chunks:
                        yield chunk

        except Exception as e:
            logger.error(f"[Awin] Chunk reading failed : {e}")

    def _parse_row(self, row: pd.Series) -> RawProduct | None:
        """Parses a single CSV row into a RawProduct."""
        try:
            title = str(row.get("product_name", "")).strip()
            if not title or title == "nan":
                return None

            # URL
            url = str(row.get("aw_deep_link", "")).strip()
            if not url or url == "nan":
                return None

            # Price
            price_raw = str(row.get("store_price", "")).strip()
            if not price_raw or price_raw == "nan":
                price_raw = str(row.get("search_price", "")).strip()

            # Brand
            brand = str(row.get("brand_name", "")).strip()
            if not brand or brand == "nan":
                brand = str(row.get("merchant_name", "")).strip()

            # Image
            image_url = str(row.get("aw_image_url", "")).strip()
            if not image_url or image_url == "nan":
                image_url = str(row.get("merchant_image_url", "")).strip()

            # Category
            category_raw = str(row.get("Fashion:category", "")).strip()
            if not category_raw or category_raw == "nan":
                category_raw = str(row.get("merchant_category", "")).strip()
            if not category_raw or category_raw == "nan":
                category_raw = str(row.get("category_name", "")).strip()

            # Source from merchant ID
            merchant_id = str(row.get("merchant_id", "")).strip()
            source = self.MERCHANT_MAP.get(merchant_id, "awin")

            # Colors
            colour = str(row.get("colour", "")).strip()
            colors = [c.strip() for c in colour.split(",")] if colour and colour != "nan" else []

            # Sizes
            size = str(row.get("Fashion:size", "")).strip()
            sizes = [s.strip() for s in size.split(",")] if size and size != "nan" else []

            # Material
            material = str(row.get("Fashion:material", "")).strip()
            if material == "nan":
                material = ""

            # Promotional
            rrp = str(row.get("rrp_price", "")).strip()
            is_promo = False
            promo_price = None
            if rrp and rrp != "nan":
                try:
                    if float(price_raw) < float(rrp):
                        is_promo = True
                        promo_price = float(rrp)
                except (ValueError, TypeError):
                    pass

            # Description
            description = str(row.get("product_short_description", "")).strip()
            if not description or description == "nan":
                description = str(row.get("description", ""))[:500]

            return RawProduct(
                source=source,
                url=url,
                title=title,
                price_raw=price_raw,
                currency=str(row.get("currency", "EUR")).strip(),
                category_raw=category_raw,
                brand=brand,
                image_url=image_url if image_url != "nan" else "",
                colors=colors,
                sizes=sizes,
                is_secondhand=False,
                extra={
                    "has_promo":    is_promo,
                    "promo_price":  promo_price,
                    "material":     material,
                    "description":  description,
                    "keywords":     str(row.get("keywords", "")).strip(),
                    "product_type": str(row.get("product_type", "")).strip(),
                    "in_stock":     str(row.get("in_stock", "")).strip(),
                    "rating":       str(row.get("average_rating", "")).strip(),
                    "reviews":      str(row.get("reviews", "")).strip(),
                    "suitable_for": str(row.get("Fashion:suitable_for", "")).strip(),
                    "savings_pct":  str(row.get("savings_percent", "")).strip(),
                },
            )

        except Exception as e:
            logger.debug(f"[Awin] Row skipped : {e}")
            return None
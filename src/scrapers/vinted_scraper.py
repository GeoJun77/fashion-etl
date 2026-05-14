# src/scrapers/vinted_scraper.py
# Scraper for Vinted FR — uses the public API with session authentication

import time
from typing import Iterator
from loguru import logger

from src.scrapers.base_scraper import BaseScraper, RawProduct


class VintedScraper(BaseScraper):
    """
    Scrapes Vinted FR via their public API.
    Requires a session cookie obtained by visiting the homepage first.
    Products are secondhand fashion items sold in France.
    """

    BASE_URL = "https://www.vinted.fr"
    API_URL = "https://www.vinted.fr/api/v2/catalog/items"

    # Fixed headers that work with the Vinted API
    API_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/",
        "X-Requested-With": "XMLHttpRequest",
    }

    HOME_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }

    # Categories to scrape with their Vinted catalog IDs
    CATEGORIES = [
        # Women — clothing
        {"id": "1904", "label": "women dresses"},
        {"id": "1931", "label": "women tops"},
        {"id": "1905", "label": "women jeans"},
        {"id": "1921", "label": "women coats"},
        {"id": "1906", "label": "women skirts"},
        {"id": "1932", "label": "women blazers"},
        {"id": "1933", "label": "women knitwear"},
        {"id": "1934", "label": "women trousers"},
        {"id": "1935", "label": "women shorts"},
        {"id": "1936", "label": "women blouses"},
        {"id": "1937", "label": "women lingerie"},
        {"id": "1938", "label": "women swimwear"},
        {"id": "1939", "label": "women sportswear"},

        # Women — shoes
        {"id": "1903", "label": "women shoes"},
        {"id": "1940", "label": "women sneakers"},
        {"id": "1941", "label": "women boots"},
        {"id": "1942", "label": "women heels"},
        {"id": "1943", "label": "women sandals"},
        {"id": "1944", "label": "women flats"},

        # Women — accessories
        {"id": "1900", "label": "women bags"},
        {"id": "1945", "label": "women jewelry"},
        {"id": "1946", "label": "women scarves"},
        {"id": "1947", "label": "women hats"},
        {"id": "1948", "label": "women belts"},
        {"id": "1949", "label": "women sunglasses"},

        # Men — clothing
        {"id": "1232", "label": "men t-shirts"},
        {"id": "1233", "label": "men jeans"},
        {"id": "1236", "label": "men coats"},
        {"id": "1950", "label": "men shirts"},
        {"id": "1951", "label": "men trousers"},
        {"id": "1952", "label": "men shorts"},
        {"id": "1953", "label": "men knitwear"},
        {"id": "1954", "label": "men blazers"},
        {"id": "1955", "label": "men sportswear"},
        {"id": "1956", "label": "men swimwear"},

        # Men — shoes
        {"id": "1229", "label": "men shoes"},
        {"id": "1957", "label": "men sneakers"},
        {"id": "1958", "label": "men boots"},
        {"id": "1959", "label": "men sandals"},

        # Men — accessories
        {"id": "1960", "label": "men bags"},
        {"id": "1961", "label": "men jewelry"},
        {"id": "1962", "label": "men hats"},
        {"id": "1963", "label": "men belts"},
        {"id": "1964", "label": "men sunglasses"},

        # Girls — clothing
        {"id": "1821", "label": "girls dresses"},
        {"id": "1965", "label": "girls tops"},
        {"id": "1966", "label": "girls jeans"},
        {"id": "1967", "label": "girls coats"},
        {"id": "1968", "label": "girls skirts"},
        {"id": "1969", "label": "girls sportswear"},

        # Girls — shoes
        {"id": "1970", "label": "girls shoes"},
        {"id": "1971", "label": "girls sneakers"},
        {"id": "1972", "label": "girls boots"},

        # Boys — clothing
        {"id": "1822", "label": "boys t-shirts"},
        {"id": "1973", "label": "boys shirts"},
        {"id": "1974", "label": "boys jeans"},
        {"id": "1975", "label": "boys coats"},
        {"id": "1976", "label": "boys shorts"},
        {"id": "1977", "label": "boys sportswear"},

        # Boys — shoes
        {"id": "1978", "label": "boys shoes"},
        {"id": "1979", "label": "boys sneakers"},
        {"id": "1980", "label": "boys boots"},
    ]

    def __init__(self):
        super().__init__("vinted")
        self._authenticate()

    def _authenticate(self) -> None:
        """
        Visits the Vinted homepage to obtain session cookies.
        These cookies are required to call the API.
        """
        logger.info("[Vinted] Authenticating via homepage...")
        try:
            self.session.get(
                self.BASE_URL,
                headers=self.HOME_HEADERS,
                timeout=30,
            )
            logger.info("[Vinted] Session cookies obtained")
        except Exception as e:
            logger.error(f"[Vinted] Authentication failed : {e}")

    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """Scrapes all configured categories until max_products is reached."""
        collected = 0

        for category in self.CATEGORIES:
            if collected >= max_products:
                break

            logger.info(f"[Vinted] Scraping category : {category['label']}")

            # Calculate how many products to fetch from this category
            remaining = max_products - collected
            per_page = min(remaining, 96)  # Vinted allows max 96 per page

            products = self._scrape_category(
                category_id=category["id"],
                category_label=category["label"],
                per_page=per_page,
            )

            for product in products:
                yield product
                collected += 1
                if collected >= max_products:
                    break

    def _scrape_category(
        self,
        category_id: str,
        category_label: str,
        per_page: int,
    ) -> list[RawProduct]:
        """Fetches products from a single Vinted category via the API."""
        try:
            response = self.session.get(
                self.API_URL,
                headers=self.API_HEADERS,
                params={
                    "per_page":   per_page,
                    "order":      "newest_first",
                    "catalog_id": category_id,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

        except Exception as e:
            logger.error(f"[Vinted] API call failed for {category_label} : {e}")
            return []

        items = data.get("items", [])
        logger.info(f"[Vinted] {len(items)} items found in {category_label}")

        products = []
        for item in items:
            product = self._parse_item(item, category_label)
            if product:
                products.append(product)

        # Respect rate limiting between category requests
        time.sleep(2)
        return products

    def _parse_item(self, item: dict, category_label: str) -> RawProduct | None:
        """Parses a single Vinted API item into a RawProduct."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None

            # Price
            price_info = item.get("price", {})
            price_raw = str(price_info.get("amount", ""))

            # URL
            path = item.get("path", "")
            url = f"{self.BASE_URL}{path}"

            # Brand
            brand = item.get("brand_title", "")

            # Image
            photo = item.get("photo", {})
            image_url = photo.get("url", "") if photo else ""

            # Size
            size_info = item.get("size_title", "")
            sizes = [size_info] if size_info else []

            return RawProduct(
                source="vinted",
                url=url,
                title=title,
                price_raw=price_raw,
                currency="EUR",
                category_raw=category_label,
                brand=brand,
                image_url=image_url,
                sizes=sizes,
                is_secondhand=True,
                extra={
                    "item_id":    str(item.get("id", "")),
                    "is_visible": item.get("is_visible", True),
                },
            )

        except Exception as e:
            logger.debug(f"[Vinted] Item skipped : {e}")
            return None
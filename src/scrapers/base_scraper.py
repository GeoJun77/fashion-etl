# src/scrapers/base_scraper.py
# Base class for all scrapers — handles retries, rate-limiting and headers

import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

import requests
from bs4 import BeautifulSoup
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import settings


@dataclass
class RawProduct:
    """Represents a raw product before any cleaning."""
    source: str
    url: str
    title: str
    price_raw: str
    currency: str = "EUR"
    category_raw: str = ""
    brand: str = ""
    image_url: str = ""
    is_secondhand: bool = False
    colors: list = field(default_factory=list)
    sizes: list = field(default_factory=list)
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    extra: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """
    Base scraper class.
    Handles : retries, rate-limiting, rotating user-agents.
    Every specific scraper must inherit from this class.
    """

    # Realistic user-agents to avoid being blocked
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    ]

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = self._build_session()
        self._request_count = 0
        logger.info(f"[{self.source_name}] Scraper initialized")

    def _build_session(self) -> requests.Session:
        """Creates a session with automatic retry on failure."""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,                                        # max 3 attempts
            backoff_factor=1.5,                             # waits 1.5s, 3s, 4.5s between attempts
            status_forcelist=[429, 500, 502, 503, 504],     # retry on these HTTP errors
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get_headers(self) -> dict:
        """Returns realistic headers that closely mimic a real browser."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Cache-Control": "max-age=0",
        }

    def get(self, url: str) -> BeautifulSoup | None:
        """
        Sends a GET request with rate-limiting.
        Returns a BeautifulSoup object or None if the request fails.
        """
        # Wait between requests to avoid being blocked
        if self._request_count > 0:
            delay = settings.scrape_delay * random.uniform(0.8, 1.2)
            logger.debug(f"[{self.source_name}] Waiting {delay:.1f}s...")
            time.sleep(delay)

        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            self._request_count += 1
            logger.debug(f"[{self.source_name}] GET {url} → {response.status_code}")
            return BeautifulSoup(response.text, "lxml")

        except requests.exceptions.HTTPError as e:
            logger.error(f"[{self.source_name}] HTTP error : {e}")
        except requests.exceptions.Timeout:
            logger.warning(f"[{self.source_name}] Timeout : {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.source_name}] Network error : {e}")

        return None

    @abstractmethod
    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """
        Yields raw products one by one.
        Must be implemented by each specific scraper.
        """
        ...

    def run(self, max_products: int | None = None) -> list[RawProduct]:
        """Runs the scraper and returns the list of collected products."""
        limit = max_products or settings.max_products
        products = []

        logger.info(f"[{self.source_name}] Starting scrape (max={limit})")

        for product in self.scrape(limit):
            products.append(product)
            if len(products) >= limit:
                break

        logger.info(f"[{self.source_name}] Done : {len(products)} products collected")
        return products
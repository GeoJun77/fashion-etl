# src/scrapers/__init__.py
# Exposes all scrapers from a single import point

from src.scrapers.awin_scraper import AwinScraper
from src.scrapers.base_scraper import BaseScraper, RawProduct
from src.scrapers.mock_scraper import MockScraper
from src.scrapers.vinted_scraper import VintedScraper

__all__ = [
    "AwinScraper",
    "BaseScraper",
    "MockScraper",
    "RawProduct",
    "VintedScraper",
]

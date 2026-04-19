# src/scrapers/__init__.py
# Exposes all scrapers from a single import point

from src.scrapers.base_scraper import BaseScraper, RawProduct
from src.scrapers.zalando_scraper import ZalandoScraper
from src.scrapers.asos_scraper import AsosScraper

__all__ = [
    "BaseScraper",
    "RawProduct",
    "ZalandoScraper",
    "AsosScraper",
]
# tests/test_pipeline.py
# Unit tests for the full ETL pipeline

import pytest
from src.scrapers.mock_scraper import MockScraper
from src.scrapers.base_scraper import RawProduct
from src.transformers.cleaner import Cleaner, CleanProduct
from src.quality.checks import QualityChecker
from src.loaders.sql_loader import init_db, load_products


# --- Scraper tests ---

def test_mock_scraper_returns_products():
    """MockScraper should return the requested number of products."""
    scraper = MockScraper()
    products = scraper.run(max_products=10)
    assert len(products) == 10


def test_mock_scraper_product_has_required_fields():
    """Every product should have a source, url, title and price."""
    scraper = MockScraper()
    products = scraper.run(max_products=5)
    for p in products:
        assert p.source != ""
        assert p.url != ""
        assert p.title != ""
        assert p.price_raw != ""


def test_mock_scraper_product_has_sizes_and_colors():
    """Every product should have sizes and colors."""
    scraper = MockScraper()
    products = scraper.run(max_products=20)
    for p in products:
        assert isinstance(p.colors, list)
        assert isinstance(p.sizes, list)


# --- Cleaner tests ---

def test_cleaner_returns_clean_products():
    """Cleaner should return the same number of valid products."""
    scraper = MockScraper()
    raw = scraper.run(max_products=10)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    assert len(clean) == 10


def test_cleaner_normalizes_category():
    """Cleaner should map raw categories to normalized ones."""
    scraper = MockScraper()
    raw = scraper.run(max_products=50)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    for p in clean:
        assert "_" in p.category or p.category == "other"


def test_cleaner_generates_slug():
    """Every clean product should have a non-empty slug."""
    scraper = MockScraper()
    raw = scraper.run(max_products=10)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    for p in clean:
        assert p.slug != ""
        assert " " not in p.slug


def test_cleaner_parses_price():
    """Cleaner should parse prices correctly."""
    scraper = MockScraper()
    raw = scraper.run(max_products=20)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    for p in clean:
        if p.price is not None:
            assert 0.5 <= p.price <= 9999.0


def test_cleaner_deduplicates():
    """Cleaner should remove duplicate URLs."""
    scraper = MockScraper()
    raw = scraper.run(max_products=10)

    # Manually duplicate the first product
    duplicate = raw[0]
    raw.append(duplicate)

    cleaner = Cleaner()
    clean = cleaner.clean(raw)

    # Should have one less product due to deduplication
    assert len(clean) == 10


# --- Loader tests ---

def test_loader_inserts_products():
    """Loader should insert products into the database."""
    init_db()
    scraper = MockScraper()
    raw = scraper.run(max_products=10)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    loaded = load_products(clean)
    assert loaded == 10


# --- Quality checks tests ---

def test_quality_checker_passes_on_clean_data():
    """Quality checker should pass on clean mock data."""
    init_db()
    scraper = MockScraper()
    raw = scraper.run(max_products=50)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    load_products(clean)

    checker = QualityChecker()
    report = checker.run(run_id=1)
    assert report.passed is True


def test_quality_checker_detects_enough_sources():
    """Quality checker should detect at least 2 sources."""
    init_db()
    scraper = MockScraper()
    raw = scraper.run(max_products=50)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    load_products(clean)

    checker = QualityChecker()
    report = checker.run(run_id=1)

    source_check = next(r for r in report.results if r.check_name == "Source coverage")
    assert source_check.passed is True
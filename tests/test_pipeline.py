# tests/test_pipeline.py
# Extract → Transform → Load with the MockScraper (synthetic data, no network)

from src.loaders.sql_loader import load_products, start_run
from src.quality.checks import QualityChecker
from src.scrapers.mock_scraper import MockScraper
from src.transformers.cleaner import Cleaner


def test_mock_scraper_returns_products():
    assert len(MockScraper().run(max_products=10)) == 10


def test_mock_products_have_required_fields():
    for p in MockScraper().run(max_products=20):
        assert p.source and p.url and p.title and p.price_raw
        assert isinstance(p.colors, list) and p.colors
        assert isinstance(p.sizes, list) and p.sizes


def test_cleaner_keeps_valid_mock_products():
    raw = MockScraper().run(max_products=50)
    clean = Cleaner().clean(raw)
    assert len(clean) >= 49   # random product ids may collide very rarely
    for p in clean:
        assert p.category != "other"
        assert p.price is not None
        assert " " not in p.slug


def test_full_pipeline_on_mock_data(db):
    run_id = start_run()
    clean = Cleaner().clean(MockScraper().run(max_products=100))
    assert load_products(clean, run_id=run_id) == len(clean)

    report = QualityChecker().run(run_id)
    assert report.passed, report.summary()

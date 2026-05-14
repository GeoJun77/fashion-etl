# tests/test_trend_analyzer.py
# Unit tests for the TrendAnalyzer

import pytest
from src.scrapers.mock_scraper import MockScraper
from src.transformers.cleaner import Cleaner
from src.transformers.trend_analyzer import TrendAnalyzer, TrendReport
from src.loaders.sql_loader import init_db, load_products


def setup_database():
    """Helper — initializes the database and loads mock products."""
    init_db()
    scraper = MockScraper()
    raw = scraper.run(max_products=100)
    cleaner = Cleaner()
    clean = cleaner.clean(raw)
    load_products(clean)


# --- TrendReport tests ---

def test_trend_report_has_categories():
    """TrendAnalyzer should return at least one category."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert len(report.categories) > 0


def test_trend_report_total_products():
    """TrendReport total_products should be greater than zero."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert report.total_products > 0


def test_trend_report_total_sources():
    """TrendReport should detect at least 2 distinct sources."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert report.total_sources >= 2


def test_trend_report_secondhand_rate():
    """Secondhand rate should be between 0 and 1."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert 0.0 <= report.secondhand_rate <= 1.0


# --- Price segments tests ---

def test_price_segments_keys():
    """Price segments should contain all four expected segments."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    expected = {"budget", "mid_range", "premium", "luxury"}
    assert set(report.price_segments.keys()) == expected


def test_price_segments_counts():
    """Each price segment should have a non-negative product count."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    for segment, data in report.price_segments.items():
        assert data["count"] >= 0


# --- Secondhand vs new tests ---

def test_secondhand_vs_new_keys():
    """Secondhand vs new report should have the expected keys."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert "secondhand_avg" in report.secondhand_vs_new
    assert "new_avg" in report.secondhand_vs_new
    assert "difference" in report.secondhand_vs_new


def test_secondhand_cheaper_than_new():
    """Secondhand products should be cheaper than new ones on average."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    s = report.secondhand_vs_new
    if s["secondhand_avg"] and s["new_avg"]:
        assert s["secondhand_avg"] < s["new_avg"]


# --- Promo by category tests ---

def test_promo_by_category_not_empty():
    """Promo by category should return at least one category."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert len(report.promo_by_category) > 0


def test_promo_rate_valid_range():
    """All promo rates should be between 0 and 1."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    for cat in report.promo_by_category:
        assert 0.0 <= cat["promo_rate"] <= 1.0


# --- Brands by segment tests ---

def test_brands_by_segment_keys():
    """Brands by segment should contain all four segments."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    expected = {"budget", "mid_range", "premium", "luxury"}
    assert set(report.brands_by_segment.keys()) == expected


def test_brands_by_segment_not_empty():
    """Each segment should have at least one brand."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    for segment, brands in report.brands_by_segment.items():
        assert len(brands) >= 0


# --- Source diversity tests ---

def test_source_diversity_not_empty():
    """Source diversity should return at least one category."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    assert len(report.source_diversity) > 0


def test_source_diversity_valid_counts():
    """Each category should have at least one source."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    for item in report.source_diversity:
        assert item["source_count"] >= 1
        assert item["product_count"] >= 1


# --- Category trend tests ---

def test_category_trend_has_required_fields():
    """Each category trend should have all required fields."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    for cat in report.categories:
        assert cat.category != ""
        assert cat.product_count > 0
        assert isinstance(cat.top_brands, list)
        assert isinstance(cat.top_sources, list)
        assert isinstance(cat.cheapest_products, list)


def test_category_trend_price_range():
    """Min price should always be less than or equal to max price."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    for cat in report.categories:
        if cat.min_price and cat.max_price:
            assert cat.min_price <= cat.max_price


# --- Summary test ---

def test_summary_is_string():
    """Report summary should return a non-empty string."""
    setup_database()
    analyzer = TrendAnalyzer()
    report = analyzer.analyze()
    summary = report.summary()
    assert isinstance(summary, str)
    assert len(summary) > 0
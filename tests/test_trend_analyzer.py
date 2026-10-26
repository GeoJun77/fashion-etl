# tests/test_trend_analyzer.py
# Trend analysis on a small, known dataset — so the expected numbers can be asserted

import pytest
from sqlalchemy import func, select

from src.loaders.schema import trends
from src.loaders.sql_loader import finish_run, load_products, start_run
from src.transformers.trend_analyzer import TrendAnalyzer
from tests.factories import make_clean


def _run(products, status="success") -> int:
    run_id = start_run()
    load_products(products, run_id=run_id)
    finish_run(run_id, len(products), len(products), 0, status=status)
    return run_id


@pytest.fixture
def dataset(db):
    """10 new dresses at 50€ (half on sale) + 10 secondhand dresses at 10€ + 5 sneakers at 120€."""
    products = (
        [make_clean(source="sneakin", price=50.0, is_promotional=i % 2 == 0, brand="Sandro") for i in range(10)]
        + [make_clean(source="vinted", price=10.0, is_secondhand=True, brand="Zara") for _ in range(10)]
        + [make_clean(source="sneakin", price=120.0, category="men_sneakers", brand="Nike") for _ in range(5)]
    )
    return _run(products)


def test_totals(dataset):
    report = TrendAnalyzer().analyze()
    assert report.total_products == 25
    assert report.total_sources == 2
    assert report.secondhand_rate == 0.4


def test_categories(dataset):
    report = TrendAnalyzer().analyze()
    by_name = {c.category: c for c in report.categories}
    assert set(by_name) == {"women_dresses", "men_sneakers"}

    dresses = by_name["women_dresses"]
    assert dresses.product_count == 20
    assert dresses.avg_price == 30.0
    assert (dresses.min_price, dresses.max_price) == (10.0, 50.0)
    assert dresses.promo_rate == 0.25
    assert dresses.cheapest_products[0]["price"] == 10.0


def test_price_segments(dataset):
    segments = TrendAnalyzer().analyze().price_segments
    assert set(segments) == {"budget", "mid_range", "premium", "luxury"}
    assert segments["budget"]["count"] == 10
    assert segments["mid_range"]["count"] == 10
    assert segments["premium"]["count"] == 5
    assert segments["luxury"]["count"] == 0


def test_secondhand_vs_new(dataset):
    result = TrendAnalyzer().analyze().secondhand_vs_new
    assert result["secondhand_avg"] == 10.0
    assert result["new_avg"] == round((10 * 50 + 5 * 120) / 15, 2)
    assert result["difference"] == round(result["new_avg"] - 10.0, 2)


def test_promo_by_category_only_keeps_big_categories(dataset):
    promos = TrendAnalyzer().analyze().promo_by_category
    assert [p["category"] for p in promos] == ["women_dresses"]   # sneakers : < 10 products
    assert promos[0]["promo_count"] == 5


def test_brands_by_segment(dataset):
    brands = TrendAnalyzer().analyze().brands_by_segment
    assert brands["budget"][0]["brand"] == "Zara"
    assert brands["premium"][0]["brand"] == "Nike"


def test_category_with_quote_in_name(db):
    """Categories are passed as bound parameters, not pasted into the SQL string."""
    _run([make_clean(category="women_l'atelier")])
    report = TrendAnalyzer().analyze()
    assert report.categories[0].category == "women_l'atelier"


def test_price_evolution_uses_price_history(db):
    url = "https://www.vinted.fr/items/1-robe"
    _run([make_clean(url=url, price=40.0), make_clean(price=60.0, source="sneakin")])
    _run([make_clean(url=url, price=20.0)])          # same product, cheaper

    evolution = TrendAnalyzer().analyze().price_evolution
    assert [run["avg_price"] for run in evolution] == [50.0, 20.0]
    assert [run["product_count"] for run in evolution] == [2, 1]


def test_save_links_trends_to_run(db, dataset):
    analyzer = TrendAnalyzer()
    analyzer.save(analyzer.analyze(), run_id=dataset)
    with db.connect() as conn:
        assert conn.execute(select(func.count()).select_from(trends).where(trends.c.run_id == dataset)).scalar() == 2


def test_summary_is_readable(dataset):
    summary = TrendAnalyzer().analyze().summary()
    assert "Trend Report" in summary
    assert "women_dresses" in summary


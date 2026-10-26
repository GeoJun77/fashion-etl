# tests/test_quality.py
# Every quality check must be able to pass AND to fail

from sqlalchemy import select

from src.loaders.schema import quality_results
from src.loaders.sql_loader import finish_run, load_products, start_run
from src.quality.checks import QualityChecker
from tests.factories import make_clean


def _good_products(n: int = 20, **overrides) -> list:
    """n healthy products spread over two sources."""
    return [
        make_clean(source="vinted" if i % 2 else "sneakin", **overrides)
        for i in range(n)
    ]


def _run(products) -> int:
    run_id = start_run()
    loaded = load_products(products, run_id=run_id)
    finish_run(run_id, len(products), loaded, 0, status="success")
    return run_id


def _result(report, name):
    return next(r for r in report.results if r.check_name == name)


def test_healthy_run_passes(db):
    report = QualityChecker().run(_run(_good_products()))
    assert report.passed, report.summary()
    assert len(report.results) == 7


def test_checks_only_look_at_current_run(db):
    _run([make_clean(price=None) for _ in range(20)])   # old, bad run
    report = QualityChecker().run(_run(_good_products()))
    assert _result(report, "Null prices").passed


def test_empty_run_fails(db):
    report = QualityChecker().run(start_run())
    assert not report.passed
    assert report.failed_checks == ["Products loaded"]


def test_null_prices_fail(db):
    products = _good_products(18) + [make_clean(price=None), make_clean(price=None, source="sneakin")]
    report = QualityChecker().run(_run(products))
    assert not _result(report, "Null prices").passed   # 10% > 5%


def test_null_brands_fail(db):
    report = QualityChecker().run(_run(_good_products(brand="")))
    assert not _result(report, "Null brands").passed


def test_uncategorized_fail(db):
    report = QualityChecker().run(_run(_good_products(category="other")))
    assert not _result(report, "Uncategorized products").passed


def test_single_source_fails(db):
    report = QualityChecker().run(_run([make_clean(source="vinted") for _ in range(10)]))
    assert not _result(report, "Source coverage").passed


def test_volume_drop_fails(db):
    _run(_good_products(20))
    report = QualityChecker().run(_run(_good_products(4)))
    check = _result(report, "Volume vs previous run")
    assert not check.passed
    assert check.value == 0.8


def test_price_swings_fail(db):
    """Simulates the old parsing bug : '1 299,00 €' read as 1.0."""
    products = _good_products(price=1299.0)
    _run(products)
    for p in products:
        p.price = 1.0
    report = QualityChecker().run(_run(products))
    assert not _result(report, "Price swings").passed


def test_normal_price_changes_pass(db):
    products = _good_products(price=100.0)
    _run(products)
    for p in products:
        p.price = 80.0   # -20% sale
    report = QualityChecker().run(_run(products))
    assert _result(report, "Price swings").passed


def test_results_are_stored(db):
    run_id = _run(_good_products())
    QualityChecker().run(run_id)
    with db.connect() as conn:
        rows = conn.execute(select(quality_results).where(quality_results.c.run_id == run_id)).all()
    assert len(rows) == 7

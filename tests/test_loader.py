# tests/test_loader.py
# The loader upserts products and keeps one price per product per run

from sqlalchemy import func, select

from src.loaders.schema import price_history, products, scrape_runs
from src.loaders.sql_loader import finish_run, load_products, start_run
from tests.factories import make_clean


def _count(engine, table) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(table)).scalar()


def test_start_and_finish_run(db):
    run_id = start_run()
    finish_run(run_id, products_scraped=10, products_loaded=8, errors=1,
               status="partial", quality_passed=False, failed_steps=["extract:vinted"])

    with db.connect() as conn:
        row = conn.execute(select(scrape_runs).where(scrape_runs.c.id == run_id)).mappings().one()
    assert row["status"] == "partial"
    assert row["products_loaded"] == 8
    assert row["failed_steps"] == "extract:vinted"
    assert row["finished_at"] is not None


def test_load_stores_all_cleaned_fields(db):
    run_id = start_run()
    product = make_clean(colors=["noir", "blanc"], sizes=["M", "L"], material="coton", price_original=40.0)
    assert load_products([product], run_id=run_id) == 1

    with db.connect() as conn:
        row = conn.execute(select(products)).mappings().one()
    assert row["slug"] == product.slug
    assert row["colors"] == "noir,blanc"
    assert row["sizes"] == "M,L"
    assert row["material"] == "coton"
    assert row["price_original"] == 40.0
    assert row["last_run_id"] == run_id


def test_upsert_updates_product_and_keeps_price_history(db):
    url = "https://www.vinted.fr/items/42-robe"

    run_1 = start_run()
    load_products([make_clean(url=url, price=30.0)], run_id=run_1)
    run_2 = start_run()
    load_products([make_clean(url=url, price=24.0)], run_id=run_2)

    # Still one product, with the latest price...
    assert _count(db, products) == 1
    with db.connect() as conn:
        assert conn.execute(select(products.c.price)).scalar() == 24.0
        # ...and both prices in the history
        history = conn.execute(
            select(price_history.c.run_id, price_history.c.price).order_by(price_history.c.run_id)
        ).all()
    assert [tuple(h) for h in history] == [(run_1, 30.0), (run_2, 24.0)]


def test_first_seen_at_is_not_overwritten(db):
    url = "https://www.vinted.fr/items/7-pull"
    load_products([make_clean(url=url)], run_id=start_run())
    with db.connect() as conn:
        first = conn.execute(select(products.c.first_seen_at)).scalar()

    load_products([make_clean(url=url, price=99.0)], run_id=start_run())
    with db.connect() as conn:
        assert conn.execute(select(products.c.first_seen_at)).scalar() == first


def test_load_nothing(db):
    assert load_products([], run_id=start_run()) == 0

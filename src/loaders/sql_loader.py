# src/loaders/sql_loader.py
# Loads clean products into the database (SQLite or PostgreSQL, chosen by DATABASE_URL)

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import create_engine, insert, select, update
from sqlalchemy.dialects import postgresql, sqlite

from config.settings import settings
from src.loaders.schema import metadata, price_history, products, scrape_runs
from src.transformers.cleaner import CleanProduct

# Database engine — shared by the loader, the quality checks and the trend analyzer
engine = create_engine(
    settings.database_url,
    echo=False,          # Set to True to see every SQL query in the logs
    pool_pre_ping=True,  # Checks the connection is alive before using it
)


def init_db() -> None:
    """Creates the tables that do not exist yet. Safe to run multiple times."""
    metadata.create_all(engine)
    logger.info(f"Database ready ({engine.dialect.name})")


def start_run() -> int:
    """Inserts a new scrape run and returns its ID."""
    with engine.begin() as conn:
        result = conn.execute(
            insert(scrape_runs).values(started_at=datetime.now(timezone.utc), status="running")
        )
        run_id = result.inserted_primary_key[0]

    logger.info(f"[Loader] Scrape run #{run_id} started")
    return run_id


def finish_run(
    run_id: int,
    products_scraped: int,
    products_loaded: int,
    errors: int,
    status: str,
    quality_passed: bool | None = None,
    failed_steps: list[str] | None = None,
) -> None:
    """Updates the scrape run with its final stats."""
    with engine.begin() as conn:
        conn.execute(
            update(scrape_runs)
            .where(scrape_runs.c.id == run_id)
            .values(
                finished_at=datetime.now(timezone.utc),
                products_scraped=products_scraped,
                products_loaded=products_loaded,
                errors_count=errors,
                status=status,
                quality_passed=quality_passed,
                failed_steps=", ".join(failed_steps) if failed_steps else None,
            )
        )

    logger.info(f"[Loader] Run #{run_id} finished — status={status} loaded={products_loaded}")


def _dialect_insert():
    """Returns the INSERT construct supporting ON CONFLICT for the current database."""
    if engine.dialect.name == "postgresql":
        return postgresql.insert
    if engine.dialect.name == "sqlite":
        return sqlite.insert
    raise NotImplementedError(f"Upsert not supported for {engine.dialect.name}")


def _to_row(product: CleanProduct, run_id: int, now: datetime) -> dict:
    return {
        "source":         product.source,
        "url":            product.url,
        "slug":           product.slug,
        "title":          product.title,
        "brand":          product.brand or None,
        "price":          product.price,
        "price_original": product.price_original,
        "currency":       product.currency,
        "category":       product.category,
        "category_raw":   product.category_raw or None,
        "image_url":      product.image_url or None,
        "colors":         ",".join(product.colors) or None,
        "sizes":          ",".join(product.sizes) or None,
        "material":       product.material or None,
        "is_promotional": bool(product.is_promotional),
        "is_secondhand":  bool(product.is_secondhand),
        "first_seen_at":  now,
        "scraped_at":     product.scraped_at,
        "updated_at":     now,
        "last_run_id":    run_id,
    }


def load_products(clean_products: list[CleanProduct], run_id: int) -> int:
    """
    Upserts products (one row per URL) and records their price for this run
    in price_history. Everything happens in a single transaction : if anything
    fails, nothing from this run is written.
    Returns the number of products loaded.
    """
    if not clean_products:
        logger.warning("[Loader] No products to load")
        return 0

    now = datetime.now(timezone.utc)
    rows = [_to_row(p, run_id, now) for p in clean_products]

    stmt = _dialect_insert()(products)
    upsert = stmt.on_conflict_do_update(
        index_elements=["url"],
        set_={
            col: stmt.excluded[col]
            for col in rows[0]
            if col not in ("url", "source", "first_seen_at")  # first_seen_at is kept from the first insert
        },
    )

    with engine.begin() as conn:
        conn.execute(upsert, rows)

        # Map URL -> product id to fill price_history
        urls = [r["url"] for r in rows]
        ids: dict[str, int] = {}
        for start in range(0, len(urls), 500):  # stay below SQL parameter limits
            batch = urls[start:start + 500]
            ids.update(conn.execute(select(products.c.url, products.c.id).where(products.c.url.in_(batch))).all())

        conn.execute(
            insert(price_history),
            [
                {
                    "product_id":     ids[r["url"]],
                    "run_id":         run_id,
                    "price":          r["price"],
                    "is_promotional": r["is_promotional"],
                    "recorded_at":    now,
                }
                for r in rows
            ],
        )

    logger.info(f"[Loader] {len(rows)} products loaded for run #{run_id}")
    return len(rows)

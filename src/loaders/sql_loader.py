# src/loaders/sql_loader.py
# Handles loading clean products into the database

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from src.transformers.cleaner import CleanProduct


# Create the database engine
engine = create_engine(
    settings.database_url,
    echo=False,         # Set to True to see every SQL query in the logs
    pool_pre_ping=True  # Checks the connection is alive before using it
)

# Create a session factory
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """
    Creates all tables one by one.
    Safe to run multiple times — uses CREATE IF NOT EXISTS.
    """
    with engine.connect() as conn:

        # Table 1 : scrape runs log
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at      TIMESTAMP,
                products_scraped INTEGER DEFAULT 0,
                products_loaded  INTEGER DEFAULT 0,
                errors_count     INTEGER DEFAULT 0,
                status           VARCHAR(20) DEFAULT 'running'
            )
        """))

        # Table 2 : scraped products
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                source         VARCHAR(50)  NOT NULL,
                url            TEXT         NOT NULL UNIQUE,
                title          TEXT         NOT NULL,
                brand          VARCHAR(200),
                price          REAL,
                currency       VARCHAR(5)   DEFAULT 'EUR',
                category       VARCHAR(100),
                image_url      TEXT,
                is_promotional INTEGER      DEFAULT 0,
                is_secondhand  INTEGER      DEFAULT 0,
                scraped_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                updated_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Table 3 : computed trends
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trends (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                category      VARCHAR(100) NOT NULL,
                source        VARCHAR(50),
                avg_price     REAL,
                min_price     REAL,
                max_price     REAL,
                product_count INTEGER,
                promo_rate    REAL,
                top_keywords  TEXT,
                computed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.commit()

    logger.info("Database initialized successfully")


def start_run() -> int:
    """
    Inserts a new scrape run in the database.
    Returns the run ID to track progress.
    """
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO scrape_runs (started_at, status)
            VALUES (:started_at, 'running')
        """), {"started_at": datetime.now(timezone.utc)})
        conn.commit()

        # SQLite-compatible way to get the last inserted ID
        result = conn.execute(text("SELECT last_insert_rowid()"))
        run_id = result.fetchone()[0]

    logger.info(f"[Loader] Scrape run #{run_id} started")
    return run_id


def finish_run(run_id: int, products_scraped: int, products_loaded: int, errors: int, status: str = "success") -> None:
    """Updates the scrape run with final stats."""
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE scrape_runs
            SET finished_at       = :finished_at,
                products_scraped  = :products_scraped,
                products_loaded   = :products_loaded,
                errors_count      = :errors,
                status            = :status
            WHERE id = :run_id
        """), {
            "finished_at":      datetime.now(timezone.utc),
            "products_scraped": products_scraped,
            "products_loaded":  products_loaded,
            "errors":           errors,
            "status":           status,
            "run_id":           run_id,
        })
        conn.commit()

    logger.info(f"[Loader] Run #{run_id} finished — status={status} loaded={products_loaded}")


def load_products(products: list[CleanProduct]) -> int:
    """
    Loads a list of CleanProduct into the database.
    Uses upsert — updates existing products instead of creating duplicates.
    Returns the number of products successfully loaded.
    """
    if not products:
        logger.warning("[Loader] No products to load")
        return 0

    loaded = 0
    errors = 0

    with engine.connect() as conn:
        for product in products:
            try:
                conn.execute(text("""
                    INSERT INTO products (
                        source, url, title, brand, price, currency,
                        category, image_url, is_promotional, is_secondhand,
                        scraped_at, updated_at
                    ) VALUES (
                        :source, :url, :title, :brand, :price, :currency,
                        :category, :image_url, :is_promotional, :is_secondhand,
                        :scraped_at, :updated_at
                    )
                    ON CONFLICT (url) DO UPDATE SET
                        title          = EXCLUDED.title,
                        brand          = EXCLUDED.brand,
                        price          = EXCLUDED.price,
                        category       = EXCLUDED.category,
                        image_url      = EXCLUDED.image_url,
                        is_promotional = EXCLUDED.is_promotional,
                        updated_at     = EXCLUDED.updated_at
                """), {
                    "source":         product.source,
                    "url":            product.url,
                    "title":          product.title,
                    "brand":          product.brand,
                    "price":          product.price,
                    "currency":       product.currency,
                    "category":       product.category,
                    "image_url":      product.image_url,
                    "is_promotional": product.is_promotional,
                    "is_secondhand":  product.is_secondhand,
                    "scraped_at":     product.scraped_at,
                    "updated_at":     datetime.now(timezone.utc),
                })
                loaded += 1

            except Exception as e:
                logger.error(f"[Loader] Failed to load product {product.url} : {e}")
                errors += 1

        conn.commit()

    logger.info(f"[Loader] {loaded} products loaded, {errors} errors")
    return loaded
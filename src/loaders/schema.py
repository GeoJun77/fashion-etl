# src/loaders/schema.py
# Single source of truth for the database schema.
# Defined with SQLAlchemy Core so the same code creates the tables on SQLite and PostgreSQL.

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

# One row per pipeline execution
scrape_runs = Table(
    "scrape_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("products_scraped", Integer, nullable=False, default=0),
    Column("products_loaded", Integer, nullable=False, default=0),
    Column("errors_count", Integer, nullable=False, default=0),
    Column("failed_steps", Text),                      # e.g. "extract:vinted, quality"
    Column("quality_passed", Boolean),
    Column("status", String(20), nullable=False, default="running"),  # running / success / partial / failed
)

# Current state of every product (one row per product URL)
products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(50), nullable=False),
    Column("url", Text, nullable=False, unique=True),
    Column("slug", String(200)),
    Column("title", Text, nullable=False),
    Column("brand", String(200)),
    Column("price", Float),
    Column("price_original", Float),                   # price before discount, when on sale
    Column("currency", String(5), nullable=False, default="EUR"),
    Column("category", String(100), nullable=False),
    Column("category_raw", Text),
    Column("image_url", Text),
    Column("colors", Text),                            # comma-separated
    Column("sizes", Text),                             # comma-separated
    Column("material", Text),
    Column("is_promotional", Boolean, nullable=False, default=False),
    Column("is_secondhand", Boolean, nullable=False, default=False),
    Column("first_seen_at", DateTime(timezone=True)),
    Column("scraped_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    Column("last_run_id", Integer, ForeignKey("scrape_runs.id")),
    Index("ix_products_category", "category"),
    Index("ix_products_source", "source"),
    Index("ix_products_last_run_id", "last_run_id"),
)

# Price observed for each product at each run — the upsert above only keeps the latest price,
# this table keeps the history (price evolution, price drops, quality checks on price swings)
price_history = Table(
    "price_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("run_id", Integer, ForeignKey("scrape_runs.id"), nullable=False),
    Column("price", Float),
    Column("is_promotional", Boolean, nullable=False, default=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("product_id", "run_id", name="uq_price_history_product_run"),
    Index("ix_price_history_run_id", "run_id"),
)

# Result of every quality check, for every run (shown in the dashboard "Pipeline health" section)
quality_results = Table(
    "quality_results",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("scrape_runs.id"), nullable=False),
    Column("check_name", String(100), nullable=False),
    Column("passed", Boolean, nullable=False),
    Column("value", Float),
    Column("threshold", Float),
    Column("message", Text),
    Column("checked_at", DateTime(timezone=True), nullable=False),
)

# Aggregated stats per category, computed after each run
trends = Table(
    "trends",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("scrape_runs.id")),
    Column("category", String(100), nullable=False),
    Column("avg_price", Float),
    Column("min_price", Float),
    Column("max_price", Float),
    Column("product_count", Integer),
    Column("promo_rate", Float),
    Column("computed_at", DateTime(timezone=True), nullable=False),
)

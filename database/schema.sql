-- database/schema.sql
-- SQLite-compatible schema for local development
-- Will be replaced by PostgreSQL syntax in production

-- Table 1 : logs every pipeline execution
CREATE TABLE IF NOT EXISTS scrape_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at      TIMESTAMP,
    products_scraped INTEGER DEFAULT 0,
    products_loaded  INTEGER DEFAULT 0,
    errors_count     INTEGER DEFAULT 0,
    status           VARCHAR(20) DEFAULT 'running'
);

-- Table 2 : stores every scraped product
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
);

-- Table 3 : stores computed trends after each run
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
);
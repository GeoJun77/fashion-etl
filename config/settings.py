# config/settings.py
# Reads environment variables (and .env) and makes them available throughout the project

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root — used so paths work whatever the current working directory is
ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database — SQLite locally, PostgreSQL in Docker (see docker-compose.yml)
    database_url: str = f"sqlite:///{ROOT_DIR / 'fashion.db'}"

    # Scraping
    scrape_delay: float = 2.0
    max_products: int = 500  # max products per source and per run

    # Sources
    awin_feed_url: str = ""  # Awin feed URL, or a local path to a downloaded .zip feed
    use_mock: bool = False   # Synthetic data — for local development only, never in the demo DB

    # Logging
    log_level: str = "INFO"

    # Scheduling
    schedule_hours: int = 6

    # Cleaning rules
    min_price: float = 0.5
    max_price: float = 9999.0

    # Quality thresholds
    null_rate_threshold: float = 0.05        # max share of products without price
    null_brand_threshold: float = 0.20       # max share of products without brand
    uncategorized_threshold: float = 0.25    # max share of products in "other"
    min_sources: int = 2                     # min distinct sources per run
    max_volume_drop: float = 0.50            # max drop of loaded products vs previous run
    max_price_swing_rate: float = 0.05       # max share of products whose price moved > 70%


# Single instance shared across the whole project
settings = Settings()

# config/settings.py
# Reads environment variables and makes them available throughout the project

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "sqlite:///fashion.db"

    # Scraping
    scrape_delay: float = 2.0
    max_products: int = 500

    # Paths
    raw_data_dir: Path = Path("./data/raw")
    log_file: Path = Path("./logs/etl.log")

    # Logging
    log_level: str = "INFO"

    # Scheduling
    schedule_hours: int = 6

    # Quality checks
    null_rate_threshold: float = 0.05
    min_price: float = 0.5
    max_price: float = 9999.0


# Single instance shared across the whole project
settings = Settings()
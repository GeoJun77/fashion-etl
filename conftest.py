# conftest.py
# Test configuration — loaded by pytest before any test module.
#
# The tests NEVER touch fashion.db : the database URL is pointed at a temporary
# SQLite file (or at TEST_DATABASE_URL, used by the CI to run the suite on PostgreSQL)
# before the application settings are imported.

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

_tmp_dir = tempfile.mkdtemp(prefix="fashion-etl-tests-")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{Path(_tmp_dir) / 'test.db'}"
# Never call real sources from the tests, whatever the local .env contains
os.environ["AWIN_FEED_URL"] = ""
os.environ["USE_MOCK"] = "false"
os.environ["SCRAPE_DELAY"] = "0"

import pytest  # noqa: E402

from config.settings import settings  # noqa: E402
from src.loaders.schema import metadata  # noqa: E402
from src.loaders.sql_loader import engine  # noqa: E402

assert "fashion.db" not in settings.database_url, "Tests must not run against fashion.db"


@pytest.fixture
def db():
    """Gives each test an empty database."""
    metadata.drop_all(engine)
    metadata.create_all(engine)
    yield engine
    metadata.drop_all(engine)

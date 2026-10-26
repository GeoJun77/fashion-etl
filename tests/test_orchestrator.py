# tests/test_orchestrator.py
# End-to-end runs with fake sources (no network)

from sqlalchemy import select

from src.loaders.schema import scrape_runs
from src.pipeline.orchestrator import Orchestrator
from src.scrapers.base_scraper import BaseScraper
from tests.factories import make_raw


class FakeScraper(BaseScraper):
    def __init__(self, source: str, n: int = 15):
        super().__init__(source)
        self.source, self.n = source, n

    def scrape(self, max_products):
        for i in range(min(self.n, max_products)):
            yield make_raw(source=self.source, url=f"https://{self.source}.test/p/{i}")


def broken_source():
    raise ConnectionError("source is down")


def _run_status(engine, run_id):
    with engine.connect() as conn:
        return conn.execute(select(scrape_runs).where(scrape_runs.c.id == run_id)).mappings().one()


def test_successful_run(db):
    summary = Orchestrator({
        "a": lambda: FakeScraper("vinted"),
        "b": lambda: FakeScraper("sneakin"),
    }).run()

    assert summary["status"] == "success"
    assert summary["products_loaded"] == 30
    run = _run_status(db, summary["run_id"])
    assert run["status"] == "success"
    assert run["quality_passed"] is True or run["quality_passed"] == 1


def test_one_broken_source_does_not_stop_the_others(db):
    summary = Orchestrator({
        "broken": broken_source,
        "a": lambda: FakeScraper("vinted"),
        "b": lambda: FakeScraper("sneakin"),
    }).run()

    assert summary["products_loaded"] == 30
    assert summary["status"] == "partial"
    assert "extract:broken" in summary["failed_steps"]


def test_source_returning_nothing_is_reported(db):
    summary = Orchestrator({
        "empty": lambda: FakeScraper("kastner_ohler", n=0),
        "a": lambda: FakeScraper("vinted"),
        "b": lambda: FakeScraper("sneakin"),
    }).run()
    assert summary["status"] == "partial"
    assert "extract:empty" in summary["failed_steps"]


def test_failed_quality_makes_run_partial(db):
    summary = Orchestrator({"a": lambda: FakeScraper("vinted")}).run()   # only one source
    assert summary["status"] == "partial"
    assert summary["failed_checks"] == ["Source coverage"]


def test_nothing_loaded_is_a_failure(db):
    summary = Orchestrator({"broken": broken_source}).run()
    assert summary["status"] == "failed"
    assert _run_status(db, summary["run_id"])["status"] == "failed"


def test_mock_is_disabled_by_default():
    from src.pipeline.orchestrator import default_sources
    assert "mock" not in default_sources()

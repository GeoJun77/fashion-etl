# src/pipeline/orchestrator.py
# Orchestrates the full ETL pipeline : Extract → Transform → Load → Quality → Trends

from collections.abc import Callable
from datetime import datetime, timezone

from loguru import logger

from config.settings import settings
from src.loaders.sql_loader import finish_run, init_db, load_products, start_run
from src.quality.checks import QualityChecker
from src.scrapers.awin_scraper import AwinScraper
from src.scrapers.base_scraper import BaseScraper, RawProduct
from src.scrapers.mock_scraper import MockScraper
from src.scrapers.vinted_scraper import VintedScraper
from src.transformers.cleaner import Cleaner
from src.transformers.trend_analyzer import TrendAnalyzer

# A source is a name + a factory, so a failing constructor (e.g. network down)
# is caught like any other extraction error
SourceFactory = Callable[[], BaseScraper]


def default_sources() -> dict[str, SourceFactory]:
    """Sources enabled by the configuration."""
    sources: dict[str, SourceFactory] = {}
    if settings.awin_feed_url:
        sources["awin"] = lambda: AwinScraper(feed_url=settings.awin_feed_url)
    sources["vinted"] = VintedScraper
    if settings.use_mock:
        logger.warning("[Orchestrator] USE_MOCK is enabled — synthetic products will be loaded")
        sources["mock"] = MockScraper
    return sources


class Orchestrator:
    """
    Runs the full ETL pipeline in sequence and logs every run in the database.

    Run status :
      - success : every step worked and all quality checks passed
      - partial : products were loaded, but a source failed or a quality check failed
      - failed  : nothing was loaded
    """

    def __init__(self, sources: dict[str, SourceFactory] | None = None):
        init_db()
        self.sources = sources if sources is not None else default_sources()
        logger.info(f"[Orchestrator] Pipeline ready — sources : {', '.join(self.sources)}")

    def run(self) -> dict:
        """Runs one full ETL cycle and returns a summary of the run."""
        logger.info("[Orchestrator] Starting ETL pipeline...")
        start_time = datetime.now(timezone.utc)
        run_id = start_run()
        failed_steps: list[str] = []

        # --- Step 1 : Extract — one try per source, so one broken source does not stop the others ---
        raw_products: list[RawProduct] = []
        extracted_by_source: dict[str, int] = {}
        for name, factory in self.sources.items():
            try:
                products = factory().run(max_products=settings.max_products)
                raw_products.extend(products)
                extracted_by_source[name] = len(products)
                if not products:
                    logger.warning(f"[Orchestrator] {name} returned 0 products")
                    failed_steps.append(f"extract:{name}")
            except Exception as e:
                logger.exception(f"[Orchestrator] Extract failed for {name} : {e}")
                extracted_by_source[name] = 0
                failed_steps.append(f"extract:{name}")
        logger.info(f"[Orchestrator] Extracted {len(raw_products)} products {extracted_by_source}")

        # --- Step 2 : Transform ---
        clean_products = []
        try:
            clean_products = Cleaner().clean(raw_products)
        except Exception as e:
            logger.exception(f"[Orchestrator] Transform failed : {e}")
            failed_steps.append("transform")

        # --- Step 3 : Load ---
        loaded = 0
        try:
            loaded = load_products(clean_products, run_id=run_id)
        except Exception as e:
            logger.exception(f"[Orchestrator] Load failed : {e}")
            failed_steps.append("load")

        # --- Step 4 : Quality checks ---
        quality_passed = None
        failed_checks: list[str] = []
        try:
            report = QualityChecker().run(run_id=run_id)
            quality_passed = report.passed
            failed_checks = report.failed_checks
            if not report.passed:
                failed_steps.append("quality")
        except Exception as e:
            logger.exception(f"[Orchestrator] Quality checks failed : {e}")
            failed_steps.append("quality")

        # --- Step 5 : Trend analysis ---
        if loaded:
            try:
                analyzer = TrendAnalyzer()
                analyzer.save(analyzer.analyze(), run_id=run_id)
            except Exception as e:
                logger.exception(f"[Orchestrator] Trend analysis failed : {e}")
                failed_steps.append("trends")

        # --- Finish ---
        if loaded == 0:
            status = "failed"
        elif failed_steps:
            status = "partial"
        else:
            status = "success"

        finish_run(
            run_id=run_id,
            products_scraped=len(raw_products),
            products_loaded=loaded,
            errors=len(failed_steps),
            status=status,
            quality_passed=quality_passed,
            failed_steps=failed_steps,
        )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        summary = {
            "run_id":           run_id,
            "status":           status,
            "duration_seconds": round(duration, 2),
            "extracted":        extracted_by_source,
            "products_scraped": len(raw_products),
            "products_cleaned": len(clean_products),
            "products_loaded":  loaded,
            "quality_passed":   quality_passed,
            "failed_checks":    failed_checks,
            "failed_steps":     failed_steps,
        }
        logger.info(f"[Orchestrator] Pipeline finished in {duration:.1f}s — {summary}")
        return summary

# src/pipeline/orchestrator.py
# Orchestrates the full ETL pipeline : Extract → Transform → Load

from datetime import datetime
from loguru import logger

from src.scrapers.mock_scraper import MockScraper
from src.scrapers.vinted_scraper import VintedScraper
from src.transformers.cleaner import Cleaner
from src.loaders.sql_loader import init_db, start_run, finish_run, load_products
from config.settings import settings
from src.quality.checks import QualityChecker


class Orchestrator:
    """
    Runs the full ETL pipeline in sequence.
    Extract → Transform → Load
    Logs every run in the database.
    """

    def __init__(self):
        # Initialize the database tables on startup
        init_db()
        logger.info("[Orchestrator] Pipeline ready")

    def run(self) -> dict:
        """
        Runs one full ETL cycle.
        Returns a summary of the run.
        """
        logger.info("[Orchestrator] Starting ETL pipeline...")
        start_time = datetime.utcnow()
        run_id = start_run()
        errors = 0

        # --- Step 1 : Extract ---
        logger.info("[Orchestrator] Step 1 : Extract")
        raw_products = []
        try:
            # Vinted scraper — real secondhand data
            vinted = VintedScraper()
            vinted_products = vinted.run(max_products=settings.max_products // 2)
            raw_products.extend(vinted_products)

            # Mock scraper — fills in while waiting for Awin approvals
            mock = MockScraper()
            mock_products = mock.run(max_products=settings.max_products // 2)
            raw_products.extend(mock_products)

            logger.info(f"[Orchestrator] Total extracted : {len(raw_products)} products")
        except Exception as e:
            logger.error(f"[Orchestrator] Extract failed : {e}")
            errors += 1

        # --- Step 2 : Transform ---
        logger.info("[Orchestrator] Step 2 : Transform")
        clean_products = []
        try:
            cleaner = Cleaner()
            clean_products = cleaner.clean(raw_products)
        except Exception as e:
            logger.error(f"[Orchestrator] Transform failed : {e}")
            errors += 1

        # --- Step 3 : Load ---
        logger.info("[Orchestrator] Step 3 : Load")
        loaded = 0
        try:
            loaded = load_products(clean_products)
        except Exception as e:
            logger.error(f"[Orchestrator] Load failed : {e}")
            errors += 1
        
        # --- Step 4 : Quality checks ---
        logger.info("[Orchestrator] Step 4 : Quality checks")
        try:
            checker = QualityChecker()
            report = checker.run(run_id=run_id)
            if not report.passed:
                logger.warning("[Orchestrator] Quality checks FAILED — see report")
        except Exception as e:
            logger.error(f"[Orchestrator] Quality checks failed : {e}")
            errors += 1

        # --- Finish ---
        duration = (datetime.utcnow() - start_time).total_seconds()
        status = "success" if errors == 0 else "failed"

        finish_run(
            run_id=run_id,
            products_scraped=len(raw_products),
            products_loaded=loaded,
            errors=errors,
            status=status,
        )

        summary = {
            "run_id":           run_id,
            "status":           status,
            "duration_seconds": round(duration, 2),
            "products_scraped": len(raw_products),
            "products_cleaned": len(clean_products),
            "products_loaded":  loaded,
            "errors":           errors,
        }

        logger.info(f"[Orchestrator] Pipeline finished in {duration:.1f}s — {summary}")
        return summary
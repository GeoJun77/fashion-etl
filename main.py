# main.py
# Main entry point for the Fashion ETL pipeline
# Run once : python main.py
# Run on schedule : python main.py --schedule

import sys
from loguru import logger
from src.pipeline.orchestrator import Orchestrator
from config.settings import settings


def run_once() -> None:
    """Runs the ETL pipeline once and exits."""
    logger.info("Fashion ETL Pipeline — single run")
    orchestrator = Orchestrator()
    summary = orchestrator.run()

    print("\n--- Run Summary ---")
    for key, value in summary.items():
        print(f"{key:25} : {value}")


def run_scheduled() -> None:
    """Runs the ETL pipeline on a schedule using APScheduler."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    logger.info(f"Fashion ETL Pipeline — scheduled every {settings.schedule_hours}h")
    orchestrator = Orchestrator()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        orchestrator.run,
        trigger="interval",
        hours=settings.schedule_hours,
        id="etl_pipeline",
    )

    # Run immediately on startup
    orchestrator.run()

    logger.info(f"Scheduler started — next run in {settings.schedule_hours}h")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()


if __name__ == "__main__":
    # Check if --schedule flag is passed
    if "--schedule" in sys.argv:
        run_scheduled()
    else:
        run_once()
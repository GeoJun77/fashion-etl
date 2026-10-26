# main.py
# Main entry point for the Fashion ETL pipeline
# Run once        : python main.py
# Run on schedule : python main.py --schedule

import sys

from loguru import logger

from config.settings import settings


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    logger.add("logs/etl.log", level=settings.log_level, rotation="10 MB", retention=5)


def run_once() -> int:
    """Runs the ETL pipeline once. Returns a non-zero exit code if the run failed."""
    from src.pipeline.orchestrator import Orchestrator

    logger.info("Fashion ETL Pipeline — single run")
    summary = Orchestrator().run()

    print("\n--- Run Summary ---")
    for key, value in summary.items():
        print(f"{key:20} : {value}")
    return 1 if summary["status"] == "failed" else 0


def run_scheduled() -> None:
    """Runs the ETL pipeline every SCHEDULE_HOURS hours using APScheduler."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    from src.pipeline.orchestrator import Orchestrator

    logger.info(f"Fashion ETL Pipeline — scheduled every {settings.schedule_hours}h")
    orchestrator = Orchestrator()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        orchestrator.run,
        trigger="interval",
        hours=settings.schedule_hours,
        id="etl_pipeline",
        max_instances=1,  # never overlap two runs
    )

    # Run immediately on startup
    orchestrator.run()

    logger.info(f"Scheduler started — next run in {settings.schedule_hours}h")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    setup_logging()
    if "--schedule" in sys.argv:
        run_scheduled()
    else:
        sys.exit(run_once())

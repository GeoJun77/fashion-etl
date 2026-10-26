# scripts/report.py
# Prints the quality report of the last run and the current trend report.
#
#   python -m scripts.report

from sqlalchemy import func, select

from src.loaders.schema import scrape_runs
from src.loaders.sql_loader import engine
from src.quality.checks import QualityChecker
from src.transformers.trend_analyzer import TrendAnalyzer


def main() -> None:
    with engine.connect() as conn:
        last_run = conn.execute(select(func.max(scrape_runs.c.id))).scalar()
    if last_run is None:
        raise SystemExit("No pipeline run found — run python main.py first")

    print(QualityChecker().run(last_run, save=False).summary())
    print()
    print(TrendAnalyzer().analyze().summary())


if __name__ == "__main__":
    main()

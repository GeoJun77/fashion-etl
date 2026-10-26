# src/quality/checks.py
# Data quality checks run after each pipeline execution.
#
# Every check looks at the products recorded during the current run (price_history.run_id),
# not at the whole table — otherwise old data would hide a broken run.
# Checks that the cleaner or the schema already guarantee (price range, unique URLs,
# non-empty titles) are deliberately not repeated here : they could never fail.

from dataclasses import dataclass, field
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import insert, text

from config.settings import settings
from src.loaders.schema import quality_results
from src.loaders.sql_loader import engine

PRICE_SWING_RATIO = 0.70  # a price moving more than 70% between two runs is suspicious


@dataclass
class QualityResult:
    """Stores the result of a single quality check."""
    check_name: str
    passed: bool
    value: float
    threshold: float
    message: str


@dataclass
class QualityReport:
    """Full quality report for one pipeline run."""
    run_id: int
    generated_at: datetime
    total_products: int
    results: list[QualityResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failed_checks(self) -> list[str]:
        return [r.check_name for r in self.results if not r.passed]

    def add(self, result: QualityResult) -> None:
        self.results.append(result)

    def summary(self) -> str:
        """Returns a readable summary of the quality report."""
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"Quality Report — Run #{self.run_id} — {status}",
            f"Generated at : {self.generated_at}",
            f"Products in run : {self.total_products}",
            "---",
        ]
        for r in self.results:
            icon = "OK" if r.passed else "FAIL"
            lines.append(f"[{icon}] {r.check_name} : {r.message}")
        return "\n".join(lines)


class QualityChecker:
    """
    Runs quality checks on the products recorded during one run :
    volume, completeness (price, brand, category), source coverage,
    volume drop vs the previous run and abnormal price swings.
    """

    def run(self, run_id: int, save: bool = True) -> QualityReport:
        """Runs all quality checks, stores the results (unless save=False) and returns the report."""
        logger.info(f"[Quality] Running checks for run #{run_id}")
        params = {"run_id": run_id}

        stats = self._query_one("""
            SELECT
                COUNT(*),
                SUM(CASE WHEN p.price IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN p.brand IS NULL OR p.brand = '' THEN 1 ELSE 0 END),
                SUM(CASE WHEN p.category = 'other' THEN 1 ELSE 0 END),
                COUNT(DISTINCT p.source)
            FROM price_history ph
            JOIN products p ON p.id = ph.product_id
            WHERE ph.run_id = :run_id
        """, params)
        total, null_prices, null_brands, uncategorized, sources = (v or 0 for v in stats)

        report = QualityReport(run_id=run_id, generated_at=datetime.now(timezone.utc), total_products=total)
        report.add(self._check_volume(total))
        if total > 0:
            report.add(self._rate_check("Null prices", null_prices, total, settings.null_rate_threshold))
            report.add(self._rate_check("Null brands", null_brands, total, settings.null_brand_threshold))
            report.add(self._rate_check("Uncategorized products", uncategorized, total,
                                        settings.uncategorized_threshold))
            report.add(self._check_source_coverage(sources))
            report.add(self._check_volume_drop(run_id, total))
            report.add(self._check_price_swings(run_id))

        if save:
            self._save(report)

        status = "PASSED" if report.passed else "FAILED"
        logger.info(f"[Quality] Report {status} — {len(report.results)} checks")
        for r in report.results:
            if not r.passed:
                logger.warning(f"[Quality] FAIL — {r.check_name} : {r.message}")
        return report

    # --- Individual checks ---

    @staticmethod
    def _check_volume(total: int) -> QualityResult:
        return QualityResult(
            check_name="Products loaded",
            passed=total > 0,
            value=float(total),
            threshold=1.0,
            message=f"{total} products loaded in this run",
        )

    @staticmethod
    def _rate_check(name: str, count: int, total: int, threshold: float) -> QualityResult:
        rate = count / total
        return QualityResult(
            check_name=name,
            passed=rate <= threshold,
            value=rate,
            threshold=threshold,
            message=f"{count}/{total} ({rate:.1%}) — threshold {threshold:.0%}",
        )

    @staticmethod
    def _check_source_coverage(sources: int) -> QualityResult:
        return QualityResult(
            check_name="Source coverage",
            passed=sources >= settings.min_sources,
            value=float(sources),
            threshold=float(settings.min_sources),
            message=f"{sources} distinct sources — minimum {settings.min_sources}",
        )

    def _check_volume_drop(self, run_id: int, total: int) -> QualityResult:
        """Fails when a run loads far fewer products than the previous one (a source broke silently)."""
        previous = self._query_one("""
            SELECT COUNT(*) FROM price_history
            WHERE run_id = (
                SELECT MAX(id) FROM scrape_runs
                WHERE id < :run_id AND status IN ('success', 'partial')
            )
        """, {"run_id": run_id})[0] or 0

        if previous == 0:
            return QualityResult("Volume vs previous run", True, 0.0, settings.max_volume_drop,
                                 "no previous run to compare with")

        drop = max(0.0, 1 - total / previous)
        return QualityResult(
            check_name="Volume vs previous run",
            passed=drop <= settings.max_volume_drop,
            value=drop,
            threshold=settings.max_volume_drop,
            message=f"{total} products vs {previous} in previous run ({drop:.0%} drop)",
        )

    def _check_price_swings(self, run_id: int) -> QualityResult:
        """
        Compares each product's price with its previous recorded price.
        Many huge swings at once usually mean a parsing bug, not real price changes.
        """
        rows = self._query_all("""
            SELECT
                cur.price,
                (
                    SELECT prev.price FROM price_history prev
                    WHERE prev.product_id = cur.product_id
                    AND prev.run_id < cur.run_id
                    AND prev.price IS NOT NULL
                    ORDER BY prev.run_id DESC
                    LIMIT 1
                ) AS previous_price
            FROM price_history cur
            WHERE cur.run_id = :run_id AND cur.price IS NOT NULL
        """, {"run_id": run_id})

        compared = [(cur, prev) for cur, prev in rows if prev]
        swings = sum(1 for cur, prev in compared if abs(cur - prev) / prev > PRICE_SWING_RATIO)
        rate = swings / len(compared) if compared else 0.0
        return QualityResult(
            check_name="Price swings",
            passed=rate <= settings.max_price_swing_rate,
            value=rate,
            threshold=settings.max_price_swing_rate,
            message=(
                f"{swings}/{len(compared)} products changed price by more than {PRICE_SWING_RATIO:.0%}"
                if compared else "no previously seen products to compare"
            ),
        )

    # --- Helpers ---

    @staticmethod
    def _save(report: QualityReport) -> None:
        if not report.results:
            return
        with engine.begin() as conn:
            conn.execute(insert(quality_results), [
                {
                    "run_id": report.run_id,
                    "check_name": r.check_name,
                    "passed": r.passed,
                    "value": r.value,
                    "threshold": r.threshold,
                    "message": r.message,
                    "checked_at": report.generated_at,
                }
                for r in report.results
            ])

    @staticmethod
    def _query_one(sql: str, params: dict) -> tuple:
        with engine.connect() as conn:
            return tuple(conn.execute(text(sql), params).fetchone())

    @staticmethod
    def _query_all(sql: str, params: dict) -> list[tuple]:
        with engine.connect() as conn:
            return [tuple(r) for r in conn.execute(text(sql), params).fetchall()]

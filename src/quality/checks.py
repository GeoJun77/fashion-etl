# src/quality/checks.py
# Quality checks run after each ETL pipeline execution

from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger
from sqlalchemy import text

from src.loaders.sql_loader import engine
from config.settings import settings


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
    passed: bool = True

    def add(self, result: QualityResult) -> None:
        """Adds a check result and updates the global pass/fail status."""
        self.results.append(result)
        if not result.passed:
            self.passed = False

    def summary(self) -> str:
        """Returns a readable summary of the quality report."""
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"Quality Report — Run #{self.run_id} — {status}",
            f"Generated at : {self.generated_at}",
            f"Total products : {self.total_products}",
            "---",
        ]
        for r in self.results:
            icon = "OK" if r.passed else "FAIL"
            lines.append(f"[{icon}] {r.check_name} : {r.message}")
        return "\n".join(lines)


class QualityChecker:
    """
    Runs quality checks on the products table after each pipeline run.
    Checks : null rates, price ranges, duplicates, source coverage.
    """

    def run(self, run_id: int) -> QualityReport:
        """Runs all quality checks and returns a full report."""
        logger.info(f"[Quality] Running checks for run #{run_id}")

        total = self._count_products()
        report = QualityReport(
            run_id=run_id,
            generated_at=datetime.utcnow(),
            total_products=total,
        )

        if total == 0:
            logger.warning("[Quality] No products found in database")
            return report

        # Run all checks
        report.add(self._check_null_titles(total))
        report.add(self._check_null_prices(total))
        report.add(self._check_null_brands(total))
        report.add(self._check_null_categories(total))
        report.add(self._check_price_range())
        report.add(self._check_duplicates())
        report.add(self._check_source_coverage())

        # Log the summary
        status = "PASSED" if report.passed else "FAILED"
        logger.info(f"[Quality] Report {status} — {len(report.results)} checks")

        # Log each failed check
        for r in report.results:
            if not r.passed:
                logger.warning(f"[Quality] FAIL — {r.check_name} : {r.message}")

        return report

    # --- Individual checks ---

    def _check_null_titles(self, total: int) -> QualityResult:
        """Checks the percentage of products with empty titles."""
        count = self._query_scalar(
            "SELECT COUNT(*) FROM products WHERE title IS NULL OR title = ''"
        )
        rate = count / total
        threshold = settings.null_rate_threshold
        return QualityResult(
            check_name="Null titles",
            passed=rate <= threshold,
            value=rate,
            threshold=threshold,
            message=f"{count} null titles ({rate:.1%}) — threshold {threshold:.1%}",
        )

    def _check_null_prices(self, total: int) -> QualityResult:
        """Checks the percentage of products with missing prices."""
        count = self._query_scalar(
            "SELECT COUNT(*) FROM products WHERE price IS NULL"
        )
        rate = count / total
        threshold = settings.null_rate_threshold
        return QualityResult(
            check_name="Null prices",
            passed=rate <= threshold,
            value=rate,
            threshold=threshold,
            message=f"{count} null prices ({rate:.1%}) — threshold {threshold:.1%}",
        )

    def _check_null_brands(self, total: int) -> QualityResult:
        """Checks the percentage of products with missing brands."""
        count = self._query_scalar(
            "SELECT COUNT(*) FROM products WHERE brand IS NULL OR brand = ''"
        )
        rate = count / total
        threshold = 0.20  # Allow up to 20% missing brands
        return QualityResult(
            check_name="Null brands",
            passed=rate <= threshold,
            value=rate,
            threshold=threshold,
            message=f"{count} null brands ({rate:.1%}) — threshold {threshold:.1%}",
        )

    def _check_null_categories(self, total: int) -> QualityResult:
        """Checks the percentage of products with missing categories."""
        count = self._query_scalar(
            "SELECT COUNT(*) FROM products WHERE category IS NULL OR category = ''"
        )
        rate = count / total
        threshold = settings.null_rate_threshold
        return QualityResult(
            check_name="Null categories",
            passed=rate <= threshold,
            value=rate,
            threshold=threshold,
            message=f"{count} null categories ({rate:.1%}) — threshold {threshold:.1%}",
        )

    def _check_price_range(self) -> QualityResult:
        """Checks for products with prices outside the valid range."""
        count = self._query_scalar(f"""
            SELECT COUNT(*) FROM products
            WHERE price IS NOT NULL
            AND (price < {settings.min_price} OR price > {settings.max_price})
        """)
        passed = count == 0
        return QualityResult(
            check_name="Price range",
            passed=passed,
            value=float(count),
            threshold=0,
            message=f"{count} products with price outside [{settings.min_price}, {settings.max_price}]",
        )

    def _check_duplicates(self) -> QualityResult:
        """Checks for duplicate URLs in the products table."""
        count = self._query_scalar("""
            SELECT COUNT(*) FROM (
                SELECT url, COUNT(*) as cnt
                FROM products
                GROUP BY url
                HAVING cnt > 1
            )
        """)
        passed = count == 0
        return QualityResult(
            check_name="Duplicate URLs",
            passed=passed,
            value=float(count),
            threshold=0,
            message=f"{count} duplicate URLs found",
        )

    def _check_source_coverage(self) -> QualityResult:
        """Checks that at least 2 different sources are present."""
        count = self._query_scalar(
            "SELECT COUNT(DISTINCT source) FROM products"
        )
        min_sources = 2
        passed = count >= min_sources
        return QualityResult(
            check_name="Source coverage",
            passed=passed,
            value=float(count),
            threshold=float(min_sources),
            message=f"{count} distinct sources — minimum {min_sources}",
        )

    # --- Helpers ---

    def _count_products(self) -> int:
        """Returns the total number of products in the database."""
        return self._query_scalar("SELECT COUNT(*) FROM products")

    def _query_scalar(self, sql: str) -> int:
        """Executes a SQL query and returns a single integer value."""
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return result.fetchone()[0]
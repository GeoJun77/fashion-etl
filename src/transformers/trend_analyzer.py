# src/transformers/trend_analyzer.py
# Analyzes trends from the products stored in the database

from dataclasses import dataclass, field
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import text

from src.loaders.sql_loader import engine


@dataclass
class CategoryTrend:
    """Trend data for a single product category."""
    category: str
    product_count: int
    avg_price: float | None
    min_price: float | None
    max_price: float | None
    promo_rate: float
    top_brands: list[dict]
    top_sources: list[dict]
    cheapest_products: list[dict]


@dataclass
class TrendReport:
    """Full trend report computed from the database."""
    generated_at: datetime
    total_products: int
    total_sources: int
    categories: list[CategoryTrend] = field(default_factory=list)
    top_brands_overall: list[dict] = field(default_factory=list)
    price_segments: dict = field(default_factory=dict)
    secondhand_rate: float = 0.0
    secondhand_vs_new: dict = field(default_factory=dict)
    promo_by_category: list[dict] = field(default_factory=list)
    brands_by_segment: dict = field(default_factory=dict)
    source_diversity: list[dict] = field(default_factory=list)
    price_evolution: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        """Returns a readable summary of the trend report."""
        lines = [
            "=== Trend Report ===",
            f"Generated at     : {self.generated_at}",
            f"Total products   : {self.total_products}",
            f"Total sources    : {self.total_sources}",
            f"Secondhand rate  : {self.secondhand_rate:.1%}",
            "",
            "--- Price segments ---",
        ]
        for segment, data in self.price_segments.items():
            lines.append(
                f"  {segment:15} : {data['count']} products "
                f"— avg {data['avg_price']}€ ({data['range']})"
            )

        lines += [
            "",
            "--- Secondhand vs new ---",
            f"  Secondhand avg price : {self.secondhand_vs_new.get('secondhand_avg')}€",
            f"  New avg price        : {self.secondhand_vs_new.get('new_avg')}€",
            f"  Price difference     : {self.secondhand_vs_new.get('difference')}€",
            "",
            "--- Top promotions by category (top 5) ---",
        ]
        for cat in self.promo_by_category[:5]:
            lines.append(
                f"  {cat['category']:25} : {cat['promo_rate']:.1%} on sale "
                f"({cat['promo_count']} products)"
            )

        lines += ["", "--- Brands by price segment ---"]
        for segment, brands in self.brands_by_segment.items():
            top = ", ".join([b["brand"] for b in brands[:3]])
            lines.append(f"  {segment:15} : {top}")

        lines += ["", "--- Source diversity by category (top 5) ---"]
        for item in self.source_diversity[:5]:
            lines.append(
                f"  {item['category']:25} : {item['source_count']} sources"
            )

        if self.price_evolution:
            lines += ["", "--- Price evolution by run ---"]
            for run in self.price_evolution[-5:]:
                lines.append(
                    f"  Run #{run['run_id']} : avg {run['avg_price']}€ "
                    f"({run['product_count']} products)"
                )

        lines += ["", "--- Top 10 categories by volume ---"]
        for cat in sorted(
            self.categories,
            key=lambda x: x.product_count,
            reverse=True
        )[:10]:
            lines.append(
                f"  {cat.category:25} : {cat.product_count} products "
                f"— avg {cat.avg_price}€ "
                f"— promo {cat.promo_rate:.1%}"
            )

        lines += ["", "--- Top 10 brands overall ---"]
        for i, brand in enumerate(self.top_brands_overall[:10], 1):
            lines.append(
                f"  {i:2}. {brand['brand']:30} {brand['count']} products"
            )

        return "\n".join(lines)


class TrendAnalyzer:
    """
    Computes fashion market trends from the products table.
    Runs after each pipeline execution.
    """

    # Price segments for market analysis
    PRICE_SEGMENTS = {
        "budget":    (0,    30),
        "mid_range": (30,   100),
        "premium":   (100,  300),
        "luxury":    (300,  9999),
    }

    def analyze(self) -> TrendReport:
        """Runs the full trend analysis and returns a TrendReport."""
        logger.info("[TrendAnalyzer] Starting analysis...")

        total = self._query_scalar("SELECT COUNT(*) FROM products")
        sources = self._query_scalar("SELECT COUNT(DISTINCT source) FROM products")
        secondhand = self._query_scalar(
            "SELECT COUNT(*) FROM products WHERE is_secondhand = 1"
        )

        report = TrendReport(
            generated_at=datetime.now(timezone.utc),
            total_products=total,
            total_sources=sources,
            secondhand_rate=secondhand / total if total > 0 else 0,
        )

        if total == 0:
            logger.warning("[TrendAnalyzer] No products found")
            return report

        # Run all analyses
        report.categories        = self._analyze_by_category()
        report.top_brands_overall = self._top_brands()
        report.price_segments    = self._analyze_price_segments()
        report.secondhand_vs_new = self._analyze_secondhand_vs_new()
        report.promo_by_category = self._analyze_promo_by_category()
        report.brands_by_segment = self._analyze_brands_by_segment()
        report.source_diversity  = self._analyze_source_diversity()
        report.price_evolution   = self._analyze_price_evolution()

        logger.info(
            f"[TrendAnalyzer] Done — {len(report.categories)} categories analyzed"
        )
        return report

    def save(self, report: TrendReport) -> None:
        """Saves the trend report to the trends table in the database."""
        with engine.connect() as conn:
            for cat in report.categories:
                conn.execute(text("""
                    INSERT INTO trends (
                        category, avg_price, min_price, max_price,
                        product_count, promo_rate, computed_at
                    ) VALUES (
                        :category, :avg_price, :min_price, :max_price,
                        :product_count, :promo_rate, :computed_at
                    )
                """), {
                    "category":      cat.category,
                    "avg_price":     cat.avg_price,
                    "min_price":     cat.min_price,
                    "max_price":     cat.max_price,
                    "product_count": cat.product_count,
                    "promo_rate":    cat.promo_rate,
                    "computed_at":   report.generated_at,
                })
            conn.commit()

        logger.info(
            f"[TrendAnalyzer] {len(report.categories)} trends saved to database"
        )

    # --- Individual analysis methods ---

    def _analyze_by_category(self) -> list[CategoryTrend]:
        """Computes stats for each product category."""
        rows = self._query("""
            SELECT
                category,
                COUNT(*)                      as count,
                ROUND(AVG(price), 2)          as avg_price,
                ROUND(MIN(price), 2)          as min_price,
                ROUND(MAX(price), 2)          as max_price,
                ROUND(AVG(is_promotional), 3) as promo_rate
            FROM products
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)

        categories = []
        for row in rows:
            category = row[0]
            categories.append(CategoryTrend(
                category=category,
                product_count=row[1],
                avg_price=row[2],
                min_price=row[3],
                max_price=row[4],
                promo_rate=row[5] or 0,
                top_brands=self._top_brands_for_category(category),
                top_sources=self._top_sources_for_category(category),
                cheapest_products=self._cheapest_products_for_category(category),
            ))

        return categories

    def _analyze_price_segments(self) -> dict:
        """Splits products into price segments and computes stats per segment."""
        result = {}
        for segment, (min_p, max_p) in self.PRICE_SEGMENTS.items():
            rows = self._query(f"""
                SELECT
                    COUNT(*) as count,
                    ROUND(AVG(price), 2) as avg_price
                FROM products
                WHERE price >= {min_p} AND price < {max_p}
            """)
            row = rows[0] if rows else (0, None)
            result[segment] = {
                "count":     row[0],
                "avg_price": row[1],
                "range":     f"{min_p}€ - {max_p}€",
            }
        return result

    def _analyze_secondhand_vs_new(self) -> dict:
        """Compares average prices between secondhand and new products."""
        rows = self._query("""
            SELECT
                is_secondhand,
                ROUND(AVG(price), 2) as avg_price,
                COUNT(*)             as count
            FROM products
            WHERE price IS NOT NULL
            GROUP BY is_secondhand
        """)

        result = {"secondhand_avg": None, "new_avg": None, "difference": None}
        for row in rows:
            if row[0] == 1:
                result["secondhand_avg"] = row[1]
            else:
                result["new_avg"] = row[1]

        # Compute price difference
        if result["secondhand_avg"] and result["new_avg"]:
            result["difference"] = round(
                result["new_avg"] - result["secondhand_avg"], 2
            )

        return result

    def _analyze_promo_by_category(self) -> list[dict]:
        """Ranks categories by promotional rate — highest first."""
        rows = self._query("""
            SELECT
                category,
                COUNT(*)                      as total,
                SUM(is_promotional)           as promo_count,
                ROUND(AVG(is_promotional), 3) as promo_rate
            FROM products
            WHERE category IS NOT NULL
            GROUP BY category
            HAVING total >= 10
            ORDER BY promo_rate DESC
        """)

        return [
            {
                "category":    row[0],
                "total":       row[1],
                "promo_count": row[2],
                "promo_rate":  row[3] or 0,
            }
            for row in rows
        ]

    def _analyze_brands_by_segment(self) -> dict:
        """Returns the top brands for each price segment."""
        result = {}
        for segment, (min_p, max_p) in self.PRICE_SEGMENTS.items():
            rows = self._query(f"""
                SELECT brand, COUNT(*) as count
                FROM products
                WHERE price >= {min_p}
                AND price < {max_p}
                AND brand IS NOT NULL
                AND brand != ''
                GROUP BY brand
                ORDER BY count DESC
                LIMIT 5
            """)
            result[segment] = [
                {"brand": row[0], "count": row[1]} for row in rows
            ]

        return result

    def _analyze_source_diversity(self) -> list[dict]:
        """Returns the number of distinct sources per category."""
        rows = self._query("""
            SELECT
                category,
                COUNT(DISTINCT source) as source_count,
                COUNT(*)               as product_count
            FROM products
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY source_count DESC
        """)

        return [
            {
                "category":      row[0],
                "source_count":  row[1],
                "product_count": row[2],
            }
            for row in rows
        ]

    def _analyze_price_evolution(self) -> list[dict]:
        """
        Tracks average price evolution across pipeline runs.
        Joins products with scrape_runs via scraped_at timestamp.
        """
        rows = self._query("""
            SELECT
                sr.id                        as run_id,
                sr.started_at                as run_date,
                ROUND(AVG(p.price), 2)       as avg_price,
                COUNT(p.id)                  as product_count
            FROM scrape_runs sr
            JOIN products p
                ON DATE(p.scraped_at) = DATE(sr.started_at)
            WHERE p.price IS NOT NULL
            AND sr.status = 'success'
            GROUP BY sr.id
            ORDER BY sr.id ASC
        """)

        return [
            {
                "run_id":        row[0],
                "run_date":      str(row[1]),
                "avg_price":     row[2],
                "product_count": row[3],
            }
            for row in rows
        ]

    def _top_brands(self, limit: int = 20) -> list[dict]:
        """Returns the most frequent brands across all products."""
        rows = self._query(f"""
            SELECT brand, COUNT(*) as count
            FROM products
            WHERE brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY count DESC
            LIMIT {limit}
        """)
        return [{"brand": row[0], "count": row[1]} for row in rows]

    def _top_brands_for_category(self, category: str, limit: int = 5) -> list[dict]:
        """Returns the top brands for a specific category."""
        rows = self._query(f"""
            SELECT brand, COUNT(*) as count
            FROM products
            WHERE category = '{category}'
            AND brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY count DESC
            LIMIT {limit}
        """)
        return [{"brand": row[0], "count": row[1]} for row in rows]

    def _top_sources_for_category(self, category: str, limit: int = 5) -> list[dict]:
        """Returns the top sources for a specific category."""
        rows = self._query(f"""
            SELECT source, COUNT(*) as count
            FROM products
            WHERE category = '{category}'
            GROUP BY source
            ORDER BY count DESC
            LIMIT {limit}
        """)
        return [{"source": row[0], "count": row[1]} for row in rows]

    def _cheapest_products_for_category(
        self, category: str, limit: int = 3
    ) -> list[dict]:
        """Returns the cheapest products for a specific category."""
        rows = self._query(f"""
            SELECT title, brand, price, url
            FROM products
            WHERE category = '{category}'
            AND price IS NOT NULL
            ORDER BY price ASC
            LIMIT {limit}
        """)
        return [
            {
                "title": row[0],
                "brand": row[1],
                "price": row[2],
                "url":   row[3],
            }
            for row in rows
        ]

    # --- Helpers ---

    def _query(self, sql: str) -> list:
        """Executes a SQL query and returns all rows."""
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return result.fetchall()

    def _query_scalar(self, sql: str) -> int:
        """Executes a SQL query and returns a single value."""
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return result.fetchone()[0]
# 👗 Fashion ETL Pipeline

> An end-to-end ETL pipeline to identify fashion market trends from online product data.

🔗 **Live Dashboard** : [fashion-etl-dashboard.streamlit.app](https://fashion-etl-dashboard.streamlit.app)

---

## 📌 Project Overview

Fashion ETL is a data pipeline that automatically collects, cleans, and analyzes fashion product data from multiple e-commerce sources in France. It identifies market trends such as price evolution, promotional rates, brand distribution, and secondhand vs. new product comparisons.

This project covers the full data engineering stack :
- **Web scraping** — real product data from Vinted and Awin affiliate feeds
- **Data cleaning & transformation** — normalization, deduplication, slug generation
- **SQL loading** — upsert into SQLite (local) or PostgreSQL (production)
- **Quality checks** — automated data quality reports after each run
- **Trend analysis** — 6 market insights computed after each pipeline run
- **Dashboard** — interactive Streamlit dashboard with 8 insight sections
- **CI/CD** — automated testing and linting on every push

---

## 🏗️ Architecture

```bash
fashion-etl/
├── src/
│   ├── scrapers/          # Data extraction
│   │   ├── base_scraper.py      # Base class with retry, rate-limiting
│   │   ├── vinted_scraper.py    # Vinted FR public API
│   │   ├── awin_scraper.py      # Awin affiliate product feeds
│   │   └── mock_scraper.py      # Realistic mock data for testing
│   ├── transformers/      # Data transformation
│   │   ├── cleaner.py           # Normalization, deduplication
│   │   └── trend_analyzer.py    # Market trend computation
│   ├── loaders/           # Data loading
│   │   └── sql_loader.py        # SQLAlchemy upsert loader
│   ├── quality/           # Quality controls
│   │   └── checks.py            # 7 automated quality checks
│   └── pipeline/          # Orchestration
│       └── orchestrator.py      # ETL pipeline orchestrator
├── dashboard/
│   └── app.py             # Streamlit dashboard
├── database/
│   └── schema.sql         # SQL schema
├── config/
│   └── settings.py        # Centralized configuration
├── tests/                 # 28 unit tests
├── docker/                # Dockerfile + docker-compose
└── .github/workflows/     # CI/CD GitHub Actions
```
---

## 📊 Data Sources

| Source | Type | Products |
|---|---|---|
| **Vinted FR** | Public API (secondhand) | Real data |
| **Sneakin FR** | Awin affiliate feed | Real data |
| **Kastner & Öhler FR** | Awin affiliate feed | Real data |
| **MockScraper** | Realistic mock data | Dev & testing |

### Why these sources ?

Zalando and ASOS were the initial targets but both use Cloudflare anti-bot protection that blocks simple HTTP requests. We pivoted to :
1. **Vinted** — accessible public API, no authentication required
2. **Awin affiliate program** — official product feeds from approved merchants

Out of 31 Awin program applications, only 2 were approved (Sneakin FR and Kastner & Öhler FR). This is common for new affiliate accounts without traffic history. The pipeline architecture makes it easy to add new sources as approvals come in.

---

## 🔄 ETL Pipeline

```bash
Extract                Transform              Load
───────                ─────────              ────
Vinted API    ──┐      Cleaner        ──┐     SQL Loader    ──┐
Awin Feed     ──┼──▶ - Normalize   ─────|──▶ - Upsert    ────┼──▶ SQLite / PostgreSQL
MockScraper   ──┘     - Deduplicate   ──┘     - Log run     ──┘
- Slug gen
↓
Quality Checks (7)
↓
Trend Analyzer (6 insights)
```

### Quality Checks
After each run, 7 automated checks are performed :
- Null rate on titles, prices, brands, categories (threshold : 5%)
- Price range validation (0.5€ → 9,999€)
- Duplicate URL detection
- Source coverage (minimum 2 sources)

### Trend Insights
- Price segments (budget / mid-range / premium / luxury)
- Secondhand vs new price comparison
- Promotional rate by category
- Top brands by price segment
- Source diversity by category
- Price evolution across pipeline runs

---

## 📈 Dashboard

Live at : [fashion-etl-dashboard.streamlit.app](https://fashion-etl-dashboard.streamlit.app)

The dashboard includes 8 sections :
1. **KPI overview** — total products, sources, avg price, promotions
2. **Overview** — products by category and source
3. **Price analysis** — segments, avg by category, evolution over time
4. **Source comparison** — Sneakin vs Kastner & Öhler vs Vinted
5. **Brand analysis** — top brands overall and by price segment
6. **Promotions** — promo rate by category, current deals
7. **Trending keywords** — most frequent words in product titles
8. **Product explorer** — filterable product table

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/GeoJun77/fashion-etl.git
cd fashion-etl

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
cp .env.example .env

# 5. Run the pipeline
python main.py

# 6. Launch the dashboard
streamlit run dashboard/app.py
```

### With Docker

```bash
docker compose up --build
```

### Scheduled mode (every 6 hours)

```bash
python main.py --schedule
```

---

## ⚙️ Configuration

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Database connection URL | `sqlite:///fashion.db` |
| `MAX_PRODUCTS` | Max products per source | `500` |
| `SCRAPE_DELAY` | Delay between requests (s) | `2` |
| `SCHEDULE_HOURS` | Pipeline frequency (h) | `6` |
| `AWIN_FEED_URL` | Awin product feed URL | `` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## 🧪 Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

**28 tests** covering :
- MockScraper product generation
- Cleaner normalization, deduplication, price parsing
- SQL Loader insertion
- Quality checker checks
- Trend Analyzer insights

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Scraping | requests, BeautifulSoup4 |
| Data processing | pandas |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 |
| Scheduling | APScheduler |
| Configuration | pydantic-settings |
| Logging | loguru |
| Dashboard | Streamlit |
| Testing | pytest, pytest-cov |
| Linting | ruff |
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Deployment | Streamlit Cloud |

---

## ⚠️ Challenges & Solutions

### Cloudflare blocking (Zalando, ASOS)
Both Zalando and ASOS use advanced Cloudflare protection. Simple HTTP requests with rotating user-agents were not sufficient. We switched to the Vinted public API and Awin affiliate feeds as alternative data sources.

### Awin affiliate approvals
Applied to 31 programs — only 2 approved. This is expected for new accounts. The pipeline is designed to plug in new sources easily as approvals arrive.

### Python 3.14 compatibility
Several dependencies (`lxml`, `pydantic-core`, `pillow`) had no prebuilt wheels for Python 3.14. Solved by removing `lxml` from the dashboard requirements and using version ranges instead of pinned versions.

### psycopg2 on Windows
`psycopg2-binary` requires PostgreSQL dev libraries. Since local development uses SQLite, it was commented out and only activated in production.

---

## 📝 License

MIT

---

## 👤 Author

**Geoffroy Gankoue**

[github.com/GeoJun77](https://github.com/GeoJun77)

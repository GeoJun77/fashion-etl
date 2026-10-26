# 👗 Fashion ETL Pipeline

> An end-to-end ETL pipeline that collects French fashion e-commerce data, cleans it, checks its quality and turns it into market insights.

[![CI](https://github.com/GeoJun77/fashion-etl/actions/workflows/ci.yml/badge.svg)](https://github.com/GeoJun77/fashion-etl/actions/workflows/ci.yml)

🔗 **Live dashboard** : [fashion-etl-dashboard.streamlit.app](https://fashion-etl-dashboard.streamlit.app)

---

## 📌 Overview

I built this pipeline to answer simple market questions from real product data : how are prices distributed, who discounts the most, how much cheaper is secondhand, which brands dominate each price segment?

It covers the whole data engineering chain :

- **Extraction** from two real sources : the Vinted API (secondhand) and Awin affiliate product feeds (Sneakin FR, Kastner & Öhler FR)
- **Transformation** : price parsing for every number format, URL normalization, deduplication of size variants, one category taxonomy for all sources
- **Loading** with upserts into SQLite (local) or PostgreSQL (Docker), with a **price history** per run
- **Data quality checks** after every run, scoped to that run and stored in the database
- **Trend analysis** and an interactive **Streamlit dashboard**
- **Tests** (89, run on SQLite *and* PostgreSQL in CI), linting, Docker Compose stack

---

## 🏗️ Architecture

```
Extract                     Transform                    Load                         Checks & insights
───────                     ─────────                    ────                         ─────────────────
Vinted API      ──┐         Cleaner                      SQL loader                   QualityChecker (7 checks)
Awin feed (zip) ──┼──▶  - parse prices          ──▶  - upsert products       ──▶  TrendAnalyzer
(Mock, dev only)──┘     - normalize URLs              - price_history per run      Streamlit dashboard
                        - dedupe size variants        - scrape_runs log
                        - normalize categories
```

```
fashion-etl/
├── src/
│   ├── scrapers/           # Extraction
│   │   ├── base_scraper.py       # Retries, rate limiting, user agents
│   │   ├── vinted_scraper.py     # Vinted FR public API
│   │   ├── awin_scraper.py       # Awin product feeds (chunked CSV reading, per-merchant quotas)
│   │   └── mock_scraper.py       # Synthetic data for tests / offline dev (USE_MOCK)
│   ├── transformers/
│   │   ├── cleaner.py            # Price parsing, URL normalization, deduplication
│   │   ├── categories.py         # FR/EN keyword taxonomy shared by all sources
│   │   └── trend_analyzer.py     # Market insights
│   ├── loaders/
│   │   ├── schema.py             # Single source of truth for the schema (SQLAlchemy Core)
│   │   └── sql_loader.py         # Transactional upsert + price history
│   ├── quality/checks.py   # Data quality checks
│   └── pipeline/orchestrator.py  # Runs the steps, isolates source failures, sets the run status
├── dashboard/app.py        # Streamlit dashboard
├── scripts/                # Manual smoke tests against the real sources + report
├── tests/                  # pytest suite (temporary database, no network)
├── config/settings.py      # Configuration from environment variables / .env
├── docker/ + docker-compose.yml
└── .github/workflows/ci.yml
```

### Database

| Table | Content |
|---|---|
| `products` | Current state of each product (one row per canonical URL) |
| `price_history` | Price of each product at each run — the source for price evolution |
| `scrape_runs` | One row per run : volumes, status (`success` / `partial` / `failed`), failed steps |
| `quality_results` | Result of every quality check for every run |
| `trends` | Per-category aggregates computed after each run |

The schema is defined once in `src/loaders/schema.py` and created with `metadata.create_all()`, so the same code runs on SQLite and PostgreSQL.

---

## 📊 Data sources

| Source | Access | Type |
|---|---|---|
| **Vinted FR** | Public JSON API | Secondhand |
| **Sneakin FR** | Awin affiliate feed | New (sneakers & streetwear) |
| **Kastner & Öhler FR** | Awin affiliate feed | New (department store — home goods and perfume are filtered out) |
| MockScraper | Generated | Tests and offline development only, disabled by default |

Zalando and ASOS were my first targets, but both sit behind Cloudflare anti-bot protection, so I switched to sources that provide data officially : the Vinted API and Awin affiliate feeds. I applied to 31 Awin programs and 2 accepted me, which is common for a new affiliate account. Adding a new merchant only requires a line in `AwinScraper.MERCHANT_MAP`.

The demo database (`fashion.db`) contains **only real data** : 3,000 Awin products and 416 Vinted listings.

---

## 🔍 Data quality

Each check looks at the products recorded **in the current run**, so old data cannot hide a broken run. Results are stored in `quality_results` and shown in the dashboard.

| Check | Fails when |
|---|---|
| Products loaded | the run loaded nothing |
| Null prices | more than 5% of products have no valid price |
| Null brands | more than 20% have no brand |
| Uncategorized products | more than 25% end up in `other` |
| Source coverage | fewer than 2 sources delivered data |
| Volume vs previous run | the volume dropped by more than 50% (a source broke silently) |
| Price swings | more than 5% of products changed price by more than 70% (typical of a parsing bug) |

A run is `success` when every step and every check passed, `partial` when products were loaded but a source or a check failed, and `failed` when nothing was loaded.

---

## 📈 Dashboard

1. **KPIs** — products, sources, categories, average price, promotions, runs
2. **Overview** — products by category and by source
3. **Price analysis** — price segments, average price by category, price evolution across runs
4. **Source comparison** — volume, prices, promotion rate per source
5. **Brands** — top brands overall and per price segment
6. **Promotions** — promotion rate by category, current deals
7. **Trending keywords** — most frequent words in product titles
8. **Secondhand vs new** — price gap overall and by category
9. **Product explorer** — filterable product table
10. **Pipeline health** — last runs and quality checks

---

## 🚀 Quick start

```bash
git clone https://github.com/GeoJun77/fashion-etl.git
cd fashion-etl

python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then set AWIN_FEED_URL if you have an Awin feed

python main.py                  # one run
python main.py --schedule       # one run now, then every SCHEDULE_HOURS hours
streamlit run dashboard/app.py
```

### With Docker (PostgreSQL + scheduled pipeline + dashboard)

```bash
docker compose up --build       # dashboard on http://localhost:8501
```

### Useful scripts

```bash
python -m scripts.check_vinted      # fetch a few real Vinted products
python -m scripts.check_awin_feed   # parse a few products per Awin merchant
python -m scripts.report            # quality + trend report of the last run
```

---

## ⚙️ Configuration

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL (SQLite or PostgreSQL) | `sqlite:///<project>/fashion.db` |
| `AWIN_FEED_URL` | Awin feed URL, or local path to the downloaded `.zip` | empty (Awin skipped) |
| `USE_MOCK` | Add synthetic products (dev only) | `false` |
| `MAX_PRODUCTS` | Max products per source (per merchant for Awin) | `500` |
| `SCRAPE_DELAY` | Delay between requests (s) | `2` |
| `SCHEDULE_HOURS` | Interval for `--schedule` (h) | `6` |
| `LOG_LEVEL` | Logging level | `INFO` |

Quality thresholds can also be changed through environment variables (see `config/settings.py`).

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=src          # 89 tests, ~88% coverage
ruff check .
```

- Tests run on a **temporary database** — they never touch `fashion.db` — and never call the network.
- Set `TEST_DATABASE_URL` to run them on PostgreSQL. The CI runs the suite on both SQLite and PostgreSQL.
- Every quality check has a test proving it can fail, not only pass.

---

## ⚠️ Challenges & what I learned

**Anti-bot protection.** Zalando and ASOS block simple HTTP clients (Cloudflare). Rather than fighting it, I moved to sources that provide data officially.

**A deduplication bug that hid almost all the Awin data.** The cleaner first removed the whole query string to deduplicate URLs. Every Awin link looks like `awin1.com/pclick.php?p=<id>`, so all Awin products collapsed into a single one per run. URLs are now normalized by removing only tracking / size-variant parameters, and the Awin scraper uses the merchant's canonical product URL, which also merges size variants (a T-shirt in 5 sizes = 1 product).

**Price formats.** French sites write `1 299,00 €` (with a narrow no-break space), feeds write `100.0000`. The first parser read `1 299,00 €` as 1 €. The parser now handles thousands separators, both decimal marks and multiple prices in one string, and the *price swings* check would catch this kind of bug in production.

**Categories that did not mean anything.** Each source has its own labels (`women dresses`, `Lifestyle > Sneakers > Junior > Mixte`, `Hommes > Vêtements > Pantalons et shorts > Chinos`). A fixed lookup table left almost all Awin products in `other`. I replaced it with a FR/EN keyword taxonomy (`audience_type`, e.g. `kids_sneakers`) that reads hierarchical labels from the most specific level. I also found that the Vinted category filter was silently ignored by the API (`catalog_id` instead of `catalog_ids`), so every listing got the label of the category requested.

**Big feeds.** The Awin feed is 1.1 GB of CSV. It is read in chunks with per-merchant quotas — the feed is sorted by merchant and category, so reading the first N rows would only return T-shirts from a single shop.

**Real vs synthetic data.** Synthetic data is useful for tests but must never reach a dashboard. The mock source is disabled by default, its sources are prefixed `mock_`, and the demo database is rebuilt from real sources only.

---

## 🛠️ Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ (CI and Docker on 3.11) |
| Extraction | requests, pandas (chunked CSV) |
| Database | SQLAlchemy 2.0 Core — SQLite / PostgreSQL |
| Scheduling | APScheduler |
| Configuration | pydantic-settings |
| Logging | loguru |
| Dashboard | Streamlit (deployed on Streamlit Community Cloud) |
| Quality | pytest, pytest-cov, ruff, GitHub Actions |
| Containers | Docker, Docker Compose |

---

## 📝 License

MIT

## 👤 Author

**Geoffroy Gankoue** — [github.com/GeoJun77](https://github.com/GeoJun77)

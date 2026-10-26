# dashboard/app.py
# Streamlit dashboard for the Fashion ETL pipeline
# Shows trends, prices, brands and sources from the database

import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect

# `streamlit run dashboard/app.py` only puts dashboard/ on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings  # noqa: E402

# --- Page config ---
st.set_page_config(
    page_title="Fashion ETL Dashboard",
    page_icon="👗",
    layout="wide",
)

# --- Database connection : same DATABASE_URL as the pipeline (SQLite or PostgreSQL) ---
TABLES = ["products", "scrape_runs", "price_history", "quality_results"]


@st.cache_resource
def get_engine():
    return create_engine(settings.database_url, pool_pre_ping=True)


@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_data() -> dict:
    """Loads the tables used by the dashboard. Returns {} if the pipeline never ran."""
    engine = get_engine()
    if not set(TABLES) <= set(inspect(engine).get_table_names()):
        return {}

    with engine.connect() as conn:
        data = {table: pd.read_sql(f"SELECT * FROM {table}", conn) for table in TABLES}  # fixed table names

    # Booleans come back as 0/1 from SQLite and True/False from PostgreSQL
    for col in ["is_promotional", "is_secondhand"]:
        data["products"][col] = data["products"][col].astype(int)
    return data


# --- Load data ---
data = load_data()

if not data:
    st.error("No database found. Run the pipeline first : python main.py")
    st.stop()

products = data["products"]
runs     = data["scrape_runs"]
history  = data["price_history"]
quality  = data["quality_results"]

if products.empty:
    st.warning("The database is empty. Run the pipeline first : python main.py")
    st.stop()

# --- Sidebar ---
st.sidebar.title("⚙️ Filters")
st.sidebar.caption("Apply filters to all sections below")

all_sources    = ["All"] + sorted(products["source"].dropna().unique().tolist())
all_categories = ["All"] + sorted(products["category"].dropna().unique().tolist())

sidebar_source   = st.sidebar.selectbox("Source", all_sources)
sidebar_category = st.sidebar.selectbox("Category", all_categories)
sidebar_promo    = st.sidebar.checkbox("Promotional products only")
sidebar_secondhand = st.sidebar.checkbox("Secondhand only")

# Apply global filters
filtered = products.copy()
if sidebar_source != "All":
    filtered = filtered[filtered["source"] == sidebar_source]
if sidebar_category != "All":
    filtered = filtered[filtered["category"] == sidebar_category]
if sidebar_promo:
    filtered = filtered[filtered["is_promotional"] == 1]
if sidebar_secondhand:
    filtered = filtered[filtered["is_secondhand"] == 1]

st.sidebar.divider()
st.sidebar.metric("Products matching filters", f"{len(filtered):,}")

# --- Header ---
st.title("👗 Fashion ETL Dashboard")
last_run = runs.sort_values("id").iloc[-1] if not runs.empty else None
st.caption(
    "French fashion market trends from Vinted (secondhand) and Awin affiliate feeds (Sneakin, Kastner & Öhler)"
    + (f" — last run #{int(last_run['id'])} : {last_run['status']}, {str(last_run['started_at'])[:16]}"
       if last_run is not None else "")
)
st.divider()

# --- KPI row ---
col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Total products",     f"{len(products):,}")
col2.metric("Sources",            products["source"].nunique())
col3.metric("Categories",         products["category"].nunique())
col4.metric("Avg price",          f"{products['price'].mean():.2f}€")
col5.metric("On promotion",       f"{products['is_promotional'].sum():,}")
col6.metric("Pipeline runs",      len(runs))

st.divider()

# ================================================================
# SECTION 1 — OVERVIEW
# ================================================================
st.header("📦 Overview")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Products by category (top 15)")
    categorized = filtered[filtered["category"] != "other"]
    if len(filtered):
        st.caption(f"{1 - len(categorized) / len(filtered):.0%} of products could not be categorized (hidden)")
    by_cat = (
        categorized.groupby("category")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    st.bar_chart(by_cat.set_index("category")["count"])

with col2:
    st.subheader("Products by source")
    by_source = (
        filtered.groupby("source")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    st.bar_chart(by_source.set_index("source")["count"])

st.divider()

# ================================================================
# SECTION 2 — PRICE ANALYSIS
# ================================================================
st.header("💰 Price Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Price segments")
    bins   = [0, 30, 100, 300, 9999]
    labels = ["Budget (0-30€)", "Mid-range (30-100€)", "Premium (100-300€)", "Luxury (300€+)"]
    filtered["segment"] = pd.cut(
        filtered["price"],
        bins=bins,
        labels=labels,
        right=False,
    )
    by_segment = (
        filtered.groupby("segment", observed=True)
        .size()
        .reset_index(name="count")
    )
    st.bar_chart(by_segment.set_index("segment")["count"])

with col2:
    st.subheader("Avg price by category (top 15)")
    avg_price = (
        categorized.groupby("category")["price"]
        .mean()
        .reset_index(name="avg_price")
        .sort_values("avg_price", ascending=False)
        .head(15)
    )
    avg_price["avg_price"] = avg_price["avg_price"].round(2)
    st.bar_chart(avg_price.set_index("category")["avg_price"])

# --- Price evolution over time ---
st.subheader("📈 Price evolution over pipeline runs")
evolution = (
    history.dropna(subset=["price"])
    .merge(runs[runs["status"].isin(["success", "partial"])][["id", "started_at"]],
           left_on="run_id", right_on="id")
    .groupby("run_id")
    .agg(avg_price=("price", "mean"), median_price=("price", "median"), products=("price", "size"))
    .round(2)
)
if len(evolution) >= 2:
    evolution.index = [f"Run #{i}" for i in evolution.index]
    st.line_chart(evolution[["avg_price", "median_price"]])
else:
    st.info("Price history needs at least two pipeline runs — it is filled at every run (price_history table).")

st.divider()

# ================================================================
# SECTION 3 — SOURCE COMPARISON
# ================================================================
st.header("🏪 Source Comparison")

source_stats = (
    products.groupby("source")
    .agg(
        product_count=("id",             "count"),
        avg_price=    ("price",          "mean"),
        min_price=    ("price",          "min"),
        max_price=    ("price",          "max"),
        promo_rate=   ("is_promotional", "mean"),
        secondhand=   ("is_secondhand",  "mean"),
    )
    .reset_index()
)
source_stats["avg_price"]  = source_stats["avg_price"].round(2)
source_stats["min_price"]  = source_stats["min_price"].round(2)
source_stats["max_price"]  = source_stats["max_price"].round(2)
source_stats["promo_rate"] = (source_stats["promo_rate"] * 100).round(1)
source_stats["secondhand"] = (source_stats["secondhand"] * 100).round(1)
source_stats.columns       = [
    "Source", "Products", "Avg price (€)",
    "Min price (€)", "Max price (€)",
    "Promo rate (%)", "Secondhand (%)"
]
st.dataframe(source_stats, width="stretch")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Avg price by source")
    st.bar_chart(source_stats.set_index("Source")["Avg price (€)"])

with col2:
    st.subheader("Promo rate by source (%)")
    st.bar_chart(source_stats.set_index("Source")["Promo rate (%)"])

st.divider()

# ================================================================
# SECTION 4 — BRANDS
# ================================================================
st.header("🏆 Brand Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 15 brands overall")
    top_brands = (
        filtered[filtered["brand"].notna() & (filtered["brand"] != "")]
        .groupby("brand")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    st.bar_chart(top_brands.set_index("brand")["count"])

with col2:
    st.subheader("Brands by price segment")
    segment_labels = {
        "Budget":    (0,   30),
        "Mid-range": (30,  100),
        "Premium":   (100, 300),
        "Luxury":    (300, 9999),
    }
    selected_segment = st.selectbox(
        "Select segment",
        list(segment_labels.keys()),
    )
    min_p, max_p = segment_labels[selected_segment]
    seg_brands = (
        products[
            (products["price"] >= min_p) &
            (products["price"] < max_p) &
            products["brand"].notna() &
            (products["brand"] != "")
        ]
        .groupby("brand")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
    )
    st.bar_chart(seg_brands.set_index("brand")["count"])

st.divider()

# ================================================================
# SECTION 5 — PROMOTIONS
# ================================================================
st.header("🏷️ Promotions")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Promo rate by category (top 10)")
    promo = (
        products.groupby("category")["is_promotional"]
        .mean()
        .reset_index(name="promo_rate")
        .sort_values("promo_rate", ascending=False)
        .head(10)
    )
    promo["promo_rate"] = (promo["promo_rate"] * 100).round(1)
    st.bar_chart(promo.set_index("category")["promo_rate"])

with col2:
    st.subheader("Products on promotion right now")
    promo_products = (
        products[products["is_promotional"] == 1]
        [["title", "brand", "price", "category", "source"]]
        .sort_values("price")
        .head(20)
    )
    if promo_products.empty:
        st.info("No promotional products found.")
    else:
        st.dataframe(promo_products, width="stretch")

st.divider()

# ================================================================
# SECTION 6 — TREND KEYWORDS
# ================================================================
st.header("🔥 Trending Keywords in product titles")

# Extract words from titles
all_titles = " ".join(products["title"].dropna().str.lower().tolist())

# Remove common stop words
stop_words = {
    "de", "du", "la", "le", "les", "un", "une", "des", "en", "et",
    "for", "the", "a", "an", "in", "with", "by", "of", "to", "on",
    "noir", "blanc", "bleu", "rouge", "vert", "gris", "rose", "beige",
    "fr", "new", "men", "women", "man", "woman", "fit",
}

words = [
    w for w in re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", all_titles)
    if w.lower() not in stop_words
]

word_counts = Counter(words).most_common(30)
df_words    = pd.DataFrame(word_counts, columns=["keyword", "count"])

col1, col2 = st.columns([2, 1])

with col1:
    st.bar_chart(df_words.set_index("keyword")["count"])

with col2:
    st.dataframe(df_words, width="stretch")

st.divider()

# ================================================================
# SECTION 7 — SECONDHAND VS NEW
# ================================================================
st.header("♻️ Secondhand vs New")

col1, col2, col3 = st.columns(3)

sh_new = products[products["is_secondhand"] == 0]["price"].mean()
sh_old = products[products["is_secondhand"] == 1]["price"].mean()
diff   = round(sh_new - sh_old, 2) if sh_new and sh_old else 0

col1.metric("New avg price",        f"{sh_new:.2f}€" if sh_new else "N/A")
col2.metric("Secondhand avg price", f"{sh_old:.2f}€" if sh_old else "N/A")
col3.metric("Price difference",     f"{diff}€",       delta=f"-{diff}€ cheaper secondhand")

secondhand_by_cat = (
    products.groupby(["category", "is_secondhand"])["price"]
    .mean()
    .reset_index()
)
secondhand_by_cat["type"]  = secondhand_by_cat["is_secondhand"].map({0: "New", 1: "Secondhand"})
secondhand_by_cat["price"] = secondhand_by_cat["price"].round(2)
pivot = secondhand_by_cat.pivot(index="category", columns="type", values="price").fillna(0)
st.bar_chart(pivot.head(15))

st.divider()

# ================================================================
# SECTION 8 — PRODUCT EXPLORER
# ================================================================
st.header("🔍 Product Explorer")

col1, col2, col3 = st.columns(3)

with col1:
    exp_source = st.selectbox(
        "Source",
        ["All"] + sorted(products["source"].dropna().unique().tolist()),
        key="exp_source",
    )
with col2:
    exp_category = st.selectbox(
        "Category",
        ["All"] + sorted(products["category"].dropna().unique().tolist()),
        key="exp_category",
    )
with col3:
    exp_price = st.slider(
        "Price range (€)",
        min_value=0,
        max_value=int(products["price"].max() or 1000),
        value=(0, 500),
        key="exp_price",
    )

exp_filtered = products.copy()
if exp_source != "All":
    exp_filtered = exp_filtered[exp_filtered["source"] == exp_source]
if exp_category != "All":
    exp_filtered = exp_filtered[exp_filtered["category"] == exp_category]
exp_filtered = exp_filtered[
    (exp_filtered["price"] >= exp_price[0]) &
    (exp_filtered["price"] <= exp_price[1])
]

st.caption(f"{len(exp_filtered)} products found")
st.dataframe(
    exp_filtered[[
        "title", "brand", "price", "category",
        "source", "is_promotional", "is_secondhand"
    ]]
    .sort_values("price")
    .head(100),
    width="stretch",
)

# ================================================================
# SECTION 9 — PIPELINE HEALTH
# ================================================================
st.divider()
st.header("🩺 Pipeline Health")

recent_runs = runs.sort_values("id", ascending=False).head(10)[
    ["id", "started_at", "status", "products_scraped", "products_loaded", "quality_passed", "failed_steps"]
]
st.subheader("Last runs")
st.dataframe(recent_runs, width="stretch", hide_index=True)

if not quality.empty:
    last_quality_run = quality["run_id"].max()
    st.subheader(f"Quality checks — run #{last_quality_run}")
    checks = quality[quality["run_id"] == last_quality_run][["check_name", "passed", "message"]]
    checks["passed"] = checks["passed"].astype(bool).map({True: "✅", False: "❌"})
    st.dataframe(checks, width="stretch", hide_index=True)

# ================================================================
# FOOTER
# ================================================================
st.divider()
st.caption(
    "Fashion ETL Pipeline — Python, SQLAlchemy (SQLite / PostgreSQL), "
    "Vinted API, Awin feeds (Sneakin + Kastner & Öhler) & Streamlit"
)

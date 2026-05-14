# dashboard/app.py
# Streamlit dashboard for the Fashion ETL pipeline
# Shows trends, prices, brands and sources from the database

import sqlite3
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

# --- Page config ---
st.set_page_config(
    page_title="Fashion ETL Dashboard",
    page_icon="👗",
    layout="wide",
)

# --- Database connection ---
DB_PATH = Path(__file__).parent.parent / "fashion.db"


@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_data() -> dict:
    """Loads all data from the SQLite database."""
    if not DB_PATH.exists():
        return {}

    conn = sqlite3.connect(DB_PATH)

    data = {
        "products": pd.read_sql("SELECT * FROM products", conn),
        "trends":   pd.read_sql("SELECT * FROM trends", conn),
        "runs":     pd.read_sql("SELECT * FROM scrape_runs", conn),
    }

    conn.close()
    return data


# --- Load data ---
data = load_data()

if not data:
    st.error("No database found. Run the pipeline first : python main.py")
    st.stop()

products = data["products"]
trends   = data["trends"]
runs     = data["runs"]

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
st.caption("Real-time fashion market trends — powered by Vinted, Awin & more")
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
    st.subheader("Products by category")
    by_cat = (
        filtered.groupby("category")
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
        filtered.groupby("category")["price"]
        .mean()
        .reset_index(name="avg_price")
        .sort_values("avg_price", ascending=False)
        .head(15)
    )
    avg_price["avg_price"] = avg_price["avg_price"].round(2)
    st.bar_chart(avg_price.set_index("category")["avg_price"])

# --- Price evolution over time ---
st.subheader("📈 Price evolution over pipeline runs")
if not runs.empty and not products.empty:
    products["scraped_at"] = pd.to_datetime(products["scraped_at"], errors="coerce")
    runs["started_at"]     = pd.to_datetime(runs["started_at"], errors="coerce")

    price_evo = []
    for _, run in runs.iterrows():
        run_date  = pd.to_datetime(run["started_at"]).date()
        run_prods = products[products["scraped_at"].dt.date == run_date]
        if not run_prods.empty:
            price_evo.append({
                "Run #":     f"Run #{int(run['id'])}",
                "Avg price": round(run_prods["price"].mean(), 2),
                "Min price": round(run_prods["price"].min(), 2),
                "Max price": round(run_prods["price"].max(), 2),
            })

    if price_evo:
        df_evo = pd.DataFrame(price_evo).set_index("Run #")
        st.line_chart(df_evo)
    else:
        st.info("Not enough runs yet to show price evolution — run the pipeline a few more times.")

st.divider()

# ================================================================
# SECTION 3 — SOURCE COMPARISON
# ================================================================
st.header("🏪 Source Comparison — Sneakin vs Kastner & Öhler vs Vinted")

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
st.dataframe(source_stats, use_container_width=True)

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
        st.dataframe(promo_products, use_container_width=True)

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
    st.dataframe(df_words, use_container_width=True)

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
    use_container_width=True,
)

# ================================================================
# FOOTER
# ================================================================
st.divider()
st.caption(
    "Fashion ETL Pipeline — Built with Python, SQLite, "
    "Vinted API, Awin (Sneakin + Kastner & Öhler) & Streamlit"
)
# tests/test_loader.py
# Tests the full Extract → Clean → Load pipeline

from src.scrapers.mock_scraper import MockScraper
from src.transformers.cleaner import Cleaner
from src.loaders.sql_loader import init_db, start_run, finish_run, load_products

# Step 1 : initialize the database
print("Initializing database...")
init_db()

# Step 2 : generate mock products
print("Generating mock products...")
scraper = MockScraper()
raw_products = scraper.run(max_products=20)

# Step 3 : clean them
print("Cleaning products...")
cleaner = Cleaner()
clean_products = cleaner.clean(raw_products)

# Step 4 : start a run
run_id = start_run()

# Step 5 : load into database
print("Loading into database...")
loaded = load_products(clean_products)

# Step 6 : finish the run
finish_run(
    run_id=run_id,
    products_scraped=len(raw_products),
    products_loaded=loaded,
    errors=len(clean_products) - loaded,
)

print(f"\nDone !")
print(f"Raw products   : {len(raw_products)}")
print(f"Clean products : {len(clean_products)}")
print(f"Loaded         : {loaded}")
print(f"Run ID         : {run_id}")
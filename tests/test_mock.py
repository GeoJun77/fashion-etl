# tests/test_mock.py
# Quick test to verify the MockScraper generates realistic products

from src.scrapers.mock_scraper import MockScraper

scraper = MockScraper()
products = scraper.run(max_products=5)

for p in products:
    print("---")
    print(f"Title       : {p.title}")
    print(f"Brand       : {p.brand}")
    print(f"Price       : {p.price_raw} EUR")
    print(f"Category    : {p.category_raw}")
    print(f"Source      : {p.source}")
    print(f"Colors      : {p.colors}")
    print(f"Sizes       : {p.sizes}")
    print(f"Material    : {p.extra['material']}")
    print(f"Season      : {p.extra['season']}")
    print(f"Trends      : {p.extra['trend_keywords']}")
    print(f"Description : {p.extra['description']}")
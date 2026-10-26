# scripts/check_awin_feed.py
# Manual smoke test of the Awin feed : parses a few products per merchant and prints them.
# Needs AWIN_FEED_URL (URL or local path to the .zip feed). Not part of the test suite.
#
#   python -m scripts.check_awin_feed

from collections import Counter

from config.settings import settings
from src.scrapers.awin_scraper import AwinScraper
from src.transformers.cleaner import Cleaner


def main() -> None:
    if not settings.awin_feed_url:
        raise SystemExit("AWIN_FEED_URL is not set (see .env.example)")

    raw = AwinScraper(feed_url=settings.awin_feed_url).run(max_products=5)
    clean = Cleaner().clean(raw)

    print(f"\n{len(clean)} products — {dict(Counter(p.source for p in clean))}\n")
    for p in clean:
        promo = f" (was {p.price_original}€)" if p.is_promotional else ""
        print(f"[{p.source}] {p.title} — {p.brand} — {p.price}€{promo} — {p.category}")
        print(f"    {p.url}")


if __name__ == "__main__":
    main()

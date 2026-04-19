# src/scrapers/asos_scraper.py
# Scraper for ASOS — extracts products from listing pages

from typing import Iterator
from loguru import logger
from src.scrapers.base_scraper import BaseScraper, RawProduct


class AsosScraper(BaseScraper):
    """
    Scrapes ASOS FR listing pages.
    Targets multiple categories : women, men, girls and boys.
    """

    # Category pages to scrape
    CATEGORIES = [
        # Women — tops
        {"url": "https://www.asos.com/fr/femmes/robes/cat/?cid=8799",          "label": "women dresses"},
        {"url": "https://www.asos.com/fr/femmes/tops/cat/?cid=4169",           "label": "women tops"},
        {"url": "https://www.asos.com/fr/femmes/t-shirts/cat/?cid=4745",       "label": "women t-shirts"},
        {"url": "https://www.asos.com/fr/femmes/pulls/cat/?cid=4921",          "label": "women knitwear"},

        # Women — bottoms
        {"url": "https://www.asos.com/fr/femmes/jeans/cat/?cid=4423",          "label": "women jeans"},
        {"url": "https://www.asos.com/fr/femmes/jupes/cat/?cid=4821",          "label": "women skirts"},
        {"url": "https://www.asos.com/fr/femmes/pantalons/cat/?cid=4369",      "label": "women trousers"},
        {"url": "https://www.asos.com/fr/femmes/shorts/cat/?cid=4338",         "label": "women shorts"},

        # Women — outerwear
        {"url": "https://www.asos.com/fr/femmes/manteaux/cat/?cid=4250",       "label": "women coats"},
        {"url": "https://www.asos.com/fr/femmes/vestes/cat/?cid=4547",         "label": "women blazers"},

        # Women — shoes
        {"url": "https://www.asos.com/fr/femmes/chaussures/cat/?cid=4172",     "label": "women shoes"},

        # Women — accessories
        {"url": "https://www.asos.com/fr/femmes/sacs/cat/?cid=4174",           "label": "women bags"},

        # Men — tops
        {"url": "https://www.asos.com/fr/hommes/t-shirts/cat/?cid=4922",       "label": "men t-shirts"},
        {"url": "https://www.asos.com/fr/hommes/chemises/cat/?cid=4435",       "label": "men shirts"},
        {"url": "https://www.asos.com/fr/hommes/pulls/cat/?cid=4616",          "label": "men knitwear"},

        # Men — bottoms
        {"url": "https://www.asos.com/fr/hommes/jeans/cat/?cid=4208",          "label": "men jeans"},
        {"url": "https://www.asos.com/fr/hommes/pantalons/cat/?cid=4914",      "label": "men trousers"},
        {"url": "https://www.asos.com/fr/hommes/shorts/cat/?cid=4679",         "label": "men shorts"},

        # Men — outerwear
        {"url": "https://www.asos.com/fr/hommes/manteaux/cat/?cid=4685",       "label": "men coats"},
        {"url": "https://www.asos.com/fr/hommes/vestes/cat/?cid=4331",         "label": "men blazers"},

        # Men — shoes
        {"url": "https://www.asos.com/fr/hommes/chaussures/cat/?cid=4209",     "label": "men shoes"},

        # Men — accessories
        {"url": "https://www.asos.com/fr/hommes/sacs/cat/?cid=4220",           "label": "men bags"},

        # Girls — tops
        {"url": "https://www.asos.com/fr/filles/robes/cat/?cid=9239",          "label": "girls dresses"},
        {"url": "https://www.asos.com/fr/filles/tops/cat/?cid=9236",           "label": "girls tops"},
        {"url": "https://www.asos.com/fr/filles/t-shirts/cat/?cid=9240",       "label": "girls t-shirts"},
        {"url": "https://www.asos.com/fr/filles/pulls/cat/?cid=9244",          "label": "girls knitwear"},

        # Girls — bottoms
        {"url": "https://www.asos.com/fr/filles/jeans/cat/?cid=9242",          "label": "girls jeans"},
        {"url": "https://www.asos.com/fr/filles/jupes/cat/?cid=9241",          "label": "girls skirts"},
        {"url": "https://www.asos.com/fr/filles/pantalons/cat/?cid=9243",      "label": "girls trousers"},
        {"url": "https://www.asos.com/fr/filles/shorts/cat/?cid=9245",         "label": "girls shorts"},

        # Girls — outerwear
        {"url": "https://www.asos.com/fr/filles/manteaux/cat/?cid=9246",       "label": "girls coats"},

        # Girls — shoes
        {"url": "https://www.asos.com/fr/filles/chaussures/cat/?cid=9247",     "label": "girls shoes"},

        # Boys — tops
        {"url": "https://www.asos.com/fr/garcons/t-shirts/cat/?cid=9250",      "label": "boys t-shirts"},
        {"url": "https://www.asos.com/fr/garcons/chemises/cat/?cid=9251",      "label": "boys shirts"},
        {"url": "https://www.asos.com/fr/garcons/pulls/cat/?cid=9254",         "label": "boys knitwear"},

        # Boys — bottoms
        {"url": "https://www.asos.com/fr/garcons/jeans/cat/?cid=9252",         "label": "boys jeans"},
        {"url": "https://www.asos.com/fr/garcons/pantalons/cat/?cid=9253",     "label": "boys trousers"},
        {"url": "https://www.asos.com/fr/garcons/shorts/cat/?cid=9255",        "label": "boys shorts"},

        # Boys — outerwear
        {"url": "https://www.asos.com/fr/garcons/manteaux/cat/?cid=9256",      "label": "boys coats"},

        # Boys — shoes
        {"url": "https://www.asos.com/fr/garcons/chaussures/cat/?cid=9257",    "label": "boys shoes"},
    ]

    def __init__(self):
        super().__init__("asos")

    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """Scrapes all configured categories until max_products is reached."""
        collected = 0

        for category in self.CATEGORIES:
            if collected >= max_products:
                break

            logger.info(f"[ASOS] Scraping category : {category['label']}")
            soup = self.get(category["url"])

            if not soup:
                logger.warning(f"[ASOS] Could not fetch : {category['url']}")
                continue

            # ASOS wraps each product in an <article> tag
            articles = soup.find_all("article")
            logger.info(f"[ASOS] Found {len(articles)} articles on page")

            for article in articles:
                if collected >= max_products:
                    break

                product = self._parse_article(article, category["label"])
                if product:
                    yield product
                    collected += 1

    def _parse_article(self, article, category_label: str) -> RawProduct | None:
        """Extracts product data from a single article HTML element."""
        try:
            # Extract title
            title_el = article.find("h2")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)

            # Extract URL
            link_el = article.find("a", href=True)
            if not link_el:
                return None
            url = link_el["href"]
            if not url.startswith("http"):
                url = f"https://www.asos.com{url}"

            # Extract price
            price_el = article.find("span", attrs={"data-auto": "product-price"})
            if not price_el:
                price_el = article.find("span", class_=lambda c: c and "price" in c.lower())
            price_raw = price_el.get_text(strip=True) if price_el else ""

            # Extract brand
            brand_el = article.find("p", class_=lambda c: c and "brand" in c.lower())
            brand = brand_el.get_text(strip=True) if brand_el else ""

            # Extract image
            img_el = article.find("img")
            image_url = img_el.get("src", "") if img_el else ""

            if not title:
                return None

            return RawProduct(
                source="asos",
                url=url,
                title=title,
                price_raw=price_raw,
                category_raw=category_label,
                brand=brand,
                image_url=image_url,
            )

        except Exception as e:
            logger.debug(f"[ASOS] Article skipped : {e}")
            return None
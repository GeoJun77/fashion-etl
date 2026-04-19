# tests/debug_vinted.py
# Debugs the Vinted API response

import requests

session = requests.Session()

# Step 1 : get session cookies
session.get(
    "https://www.vinted.fr",
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
)

print(f"Cookies : {list(session.cookies.keys())}")

# Step 2 : call the API with the same session
response = session.get(
    "https://www.vinted.fr/api/v2/catalog/items",
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/",
        "X-Requested-With": "XMLHttpRequest",
    },
    params={
        "per_page": 5,
        "order": "newest_first",
        "catalog_id": "1904",
    }
)

print(f"Status       : {response.status_code}")
print(f"Content-Type : {response.headers.get('Content-Type')}")
print(f"Response     : {response.text[:500]}")
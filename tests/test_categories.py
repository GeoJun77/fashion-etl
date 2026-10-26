# tests/test_categories.py
# The category normalizer must handle the label format of every source

import pytest

from src.transformers.categories import normalize_category


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Vinted
        ("women dresses", "women_dresses"),
        ("women lingerie", "women_underwear"),
        ("women sportswear", "women_sportswear"),
        ("women sandals", "women_sandals"),
        ("men t-shirts", "men_tops"),
        ("boys shirts", "boys_shirts"),
        ("girls sneakers", "girls_sneakers"),
        # Sneakin (Awin)
        ("Lifestyle > T-shirt > Adulte > Homme", "men_tops"),
        ("Lifestyle > Soutien-gorge > Adulte > Femme", "women_underwear"),
        ("Lifestyle > Sneakers > Junior > Mixte", "kids_sneakers"),
        ("Lifestyle > Sneakers > Adulte > Mixte", "unisex_sneakers"),
        ("Natation > Short de bain > Adulte > Homme", "men_swimwear"),
        ("Lifestyle > Haut de maillot de bain > Adulte > Femme", "women_swimwear"),
        ("Lifestyle > Sac à dos > Adulte > Mixte", "unisex_bags"),
        ("Handball > Chaussures indoor > Adulte > Homme", "men_shoes"),
        # Kastner & Öhler (Awin)
        ("Hommes > Vêtements > Pantalons et shorts > Chinos", "men_trousers"),
        ("Hommes > Vêtements > Pantalons et shorts > Shorts et bermudas", "men_shorts"),
        ("Femmes > Vêtements > Chemisiers et tuniques > Blouses", "women_blouses"),
        ("Hommes > Vêtements > Sous-vêtements et pyjamas > Sous-vêtements > Chemises et hauts", "men_underwear"),
        ("Hommes > Vêtements > Costumes > Costumes modulables > Vestes modulables", "men_blazers"),
        ("Beauté > Parfums > Parfums pour femme", "beauty"),
    ],
)
def test_normalize_category(raw, expected):
    assert normalize_category(raw) == expected


def test_falls_back_on_title():
    assert normalize_category("", "Jean slim homme") == "men_jeans"


def test_unknown_label_is_other():
    assert normalize_category("Maison > Cuisine > Ustensiles") == "other"

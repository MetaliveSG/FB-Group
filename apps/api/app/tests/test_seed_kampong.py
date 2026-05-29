"""Merchant 4 — Kampong Eats: seed creates the expected entities, the owner can
log in, the public QR resolves a complete menu, and re-running is idempotent."""
from app.seed import seed_kampong
from app.tests.helpers import staff_token

EXPECTED_ITEMS = {
    "Fish Ball Noodle", "Chicken Bun", "Pork Bun", "Chicken Drumstick",
    "Burger", "Chendol", "Roti Prata (Plain)", "Teh Tarik",
    "Fish Soup (slice)", "French Fries", "Curry Rice",
}


def test_seed_kampong_creates_merchant_and_is_idempotent(client, db):
    # First run: full create (skip the customer cohort to keep the test fast).
    first = seed_kampong(db, seed_customers=False)
    assert first["status"] == "created"
    assert first["merchant_name"] == "Kampong Eats"
    assert first["items"] == 11
    assert first["outlets"] == ["Kampong Eats — Bedok", "Kampong Eats — Toa Payoh"]

    # Owner can log in via the API (RBAC + scoping wired correctly).
    assert staff_token(client, "owner@kampongeats.sg")

    # Public QR resolves the menu the user asked for — every requested item present.
    qr = client.get("/api/v1/qr/kampong-bedok-01").json()
    assert qr["outlet"]["name"] == "Kampong Eats — Bedok"
    items = {i["name"] for c in qr["menu"]["categories"] for i in c["items"]}
    assert items == EXPECTED_ITEMS, f"menu mismatch — diff: {items ^ EXPECTED_ITEMS}"
    cats = {c["name"]: [i["name"] for i in c["items"]] for c in qr["menu"]["categories"]}
    assert set(cats) == {"Hawker Mains", "Bakery", "Fried Snacks", "Drinks", "Dessert"}
    # Soup belongs with the other hawker mains (not under Fried Snacks).
    assert "Fish Soup (slice)" in cats["Hawker Mains"]
    assert "Fish Soup (slice)" not in cats["Fried Snacks"]
    # Fried Snacks shouldn't sneak any non-fried item back in.
    assert set(cats["Fried Snacks"]) == {"Chicken Drumstick", "Burger", "French Fries"}

    # Second run is a clean no-op (safe to run repeatedly against the live DB).
    again = seed_kampong(db, seed_customers=False)
    assert again["status"] == "already_exists"
    assert again["merchant_id"] == first["merchant_id"]

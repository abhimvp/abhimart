"""Integration tests for the /v1/products API.

These are integration tests, not unit tests:
- They hit real routes via the HTTP client
- They write to (and roll back from) a real Postgres database
- They test the full request→route→repo→DB→response cycle

Each test is independent. The rollback fixture in conftest.py ensures
no test pollutes the next one's data.
"""

import uuid


# ─── Health check ────────────────────────────────────────────────────────────


async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ─── Create (POST) ───────────────────────────────────────────────────────────


async def test_create_product_returns_201(client, product_payload):
    response = await client.post("/v1/products", json=product_payload)
    assert response.status_code == 201


async def test_create_product_returns_expected_fields(client, product_payload):
    response = await client.post("/v1/products", json=product_payload)
    data = response.json()

    # Server-generated fields must be present
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["is_active"] is True

    # Input fields must be echoed back
    assert data["name"] == product_payload["name"]
    assert data["sku"] == product_payload["sku"]
    assert data["category"] == product_payload["category"]
    assert float(data["price"]) == product_payload["price"]


async def test_create_product_duplicate_sku_returns_409(client, product_payload):
    await client.post("/v1/products", json=product_payload)  # first insert
    response = await client.post("/v1/products", json=product_payload)  # duplicate
    assert response.status_code == 409
    assert "SKU" in response.json()["detail"]


async def test_create_product_invalid_data_returns_422(client):
    bad_payload = {
        "name": "",  # too short (min_length=1)
        "description": "x",
        "price": -5,  # must be > 0
        "category": "toys",  # not in enum
        "sku": "X",
    }
    response = await client.post("/v1/products", json=bad_payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    # Should have multiple validation errors
    assert len(errors) >= 2


async def test_create_product_missing_required_field_returns_422(client):
    # Missing 'sku' entirely
    payload = {
        "name": "Widget",
        "description": "A widget",
        "price": 9.99,
        "category": "books",
    }
    response = await client.post("/v1/products", json=payload)
    assert response.status_code == 422


# ─── Get by ID (GET /{id}) ───────────────────────────────────────────────────


async def test_get_product_by_id(client, product_payload):
    create_response = await client.post("/v1/products", json=product_payload)
    product_id = create_response.json()["id"]

    response = await client.get(f"/v1/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["id"] == product_id


async def test_get_product_not_found_returns_404(client):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/v1/products/{fake_id}")
    assert response.status_code == 404


async def test_get_product_invalid_uuid_returns_422(client):
    response = await client.get("/v1/products/not-a-uuid")
    assert response.status_code == 422


# ─── List (GET /) ────────────────────────────────────────────────────────────


async def test_list_products_empty(client):
    response = await client.get("/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["pages"] == 0


async def test_list_products_returns_created_products(client, product_payload):
    await client.post("/v1/products", json=product_payload)

    # Create a second product (different SKU + category)
    second = {**product_payload, "sku": "TEST-APPL-001", "category": "appliances"}
    await client.post("/v1/products", json=second)

    response = await client.get("/v1/products")
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_products_filter_by_category(client, product_payload):
    await client.post("/v1/products", json=product_payload)  # electronics

    fitness = {**product_payload, "sku": "TEST-FIT-001", "category": "fitness"}
    await client.post("/v1/products", json=fitness)

    response = await client.get("/v1/products?category=electronics")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "electronics"


async def test_list_products_pagination(client, product_payload):
    # Create 3 products
    for i in range(3):
        p = {**product_payload, "sku": f"TEST-PAG-00{i}"}
        await client.post("/v1/products", json=p)

    response = await client.get("/v1/products?page=1&size=2")
    data = response.json()
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2

    response2 = await client.get("/v1/products?page=2&size=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


# ─── Update (PATCH) ──────────────────────────────────────────────────────────


async def test_update_product_partial(client, product_payload):
    create_response = await client.post("/v1/products", json=product_payload)
    product_id = create_response.json()["id"]

    response = await client.patch(
        f"/v1/products/{product_id}",
        json={"price": 899.99},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["price"]) == 899.99
    # Other fields must be unchanged
    assert data["name"] == product_payload["name"]
    assert data["sku"] == product_payload["sku"]


async def test_update_product_not_found_returns_404(client):
    fake_id = str(uuid.uuid4())
    response = await client.patch(f"/v1/products/{fake_id}", json={"price": 1.0})
    assert response.status_code == 404


# ─── Delete (DELETE) ─────────────────────────────────────────────────────────


async def test_soft_delete_sets_is_active_false(client, product_payload):
    create_response = await client.post("/v1/products", json=product_payload)
    product_id = create_response.json()["id"]

    response = await client.delete(f"/v1/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_soft_deleted_product_excluded_from_listing(client, product_payload):
    create_response = await client.post("/v1/products", json=product_payload)
    product_id = create_response.json()["id"]

    await client.delete(f"/v1/products/{product_id}")

    response = await client.get("/v1/products")
    assert response.json()["total"] == 0


async def test_soft_deleted_product_returns_404_on_get(client, product_payload):
    create_response = await client.post("/v1/products", json=product_payload)
    product_id = create_response.json()["id"]

    await client.delete(f"/v1/products/{product_id}")

    response = await client.get(f"/v1/products/{product_id}")
    assert response.status_code == 404

from __future__ import annotations

import sys
from pathlib import Path

from sqlmodel import select

from core import database
from models.db_models import (
    ECommerceSKU,
    ECommerceUser,
    ECommerceOrder,
    ECommerceOrderItem,
    ECommerceShipment,
    ECommerceShipmentEvent,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT_DIR = REPO_ROOT / "mcp_server" / "seeds" / "scripts"

if str(SEED_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SEED_SCRIPT_DIR))

from seed_ecommerce_skus import DEFAULT_CSV_PATH, seed_ecommerce_skus  # noqa: E402
from seed_ecommerce_users import DEFAULT_CSV_PATH as USERS_CSV_PATH, seed_ecommerce_users  # noqa: E402
from seed_ecommerce_orders import seed_ecommerce_orders  # noqa: E402


def test_seed_ecommerce_skus_is_idempotent() -> None:
    first_result = seed_ecommerce_skus(session_factory=database.get_session)
    second_result = seed_ecommerce_skus(session_factory=database.get_session)

    assert first_result.inserted == 20
    assert first_result.updated == 0
    assert second_result.inserted == 0
    assert second_result.updated == 20

    with database.get_session() as session:
        stored_skus = session.exec(select(ECommerceSKU)).all()
        assert len(stored_skus) == 20

        by_code = {sku.sku_code: sku for sku in stored_skus}
        assert "5004752_ea_000pns" in by_code
        assert by_code["5004752_ea_000pns"].sku_id == 840173
        assert by_code["5004752_ea_000pns"].name == "Pams Standard UHT Milk 1l"
        assert by_code["5004752_ea_000pns"].price == 2.29
        assert by_code["5004752_ea_000pns"].stock == 999
        assert by_code["5004752_ea_000pns"].description.startswith("Made using 100% fresh NZ milk")


def test_seed_csv_exists() -> None:
    assert DEFAULT_CSV_PATH.exists()
    assert USERS_CSV_PATH.exists()


def test_seed_ecommerce_users_is_idempotent() -> None:
    first_result = seed_ecommerce_users(session_factory=database.get_session)
    second_result = seed_ecommerce_users(session_factory=database.get_session)

    assert first_result.inserted == 5
    assert first_result.updated == 0
    assert second_result.inserted == 0
    assert second_result.updated == 5

    with database.get_session() as session:
        stored_users = session.exec(select(ECommerceUser)).all()
        assert len(stored_users) == 5

        by_email = {user.email: user for user in stored_users}
        assert "john@example.com" in by_email
        assert by_email["john@example.com"].user_id == 1001
        assert by_email["john@example.com"].user_name == "John Doe"
        assert by_email["john@example.com"].status == 1
        assert by_email["john@example.com"].phone == "123-456-7890"
        assert by_email["john@example.com"].create_ts == 1700000000


def test_seed_ecommerce_orders_is_idempotent() -> None:
    # Seed prerequisites
    seed_ecommerce_users(session_factory=database.get_session)
    seed_ecommerce_skus(session_factory=database.get_session)

    first_result = seed_ecommerce_orders(session_factory=database.get_session)
    second_result = seed_ecommerce_orders(session_factory=database.get_session)

    assert first_result.orders_inserted == 5
    assert first_result.orders_updated == 0
    assert first_result.items_inserted == 9
    assert first_result.items_updated == 0
    assert first_result.shipments_inserted == 4
    assert first_result.shipments_updated == 0
    assert first_result.events_inserted == 13
    assert first_result.events_updated == 0

    assert second_result.orders_inserted == 0
    assert second_result.orders_updated == 5
    assert second_result.items_inserted == 0
    assert second_result.items_updated == 9
    assert second_result.shipments_inserted == 0
    assert second_result.shipments_updated == 4
    assert second_result.events_inserted == 0
    assert second_result.events_updated == 13

    with database.get_session() as session:
        stored_orders = session.exec(select(ECommerceOrder)).all()
        assert len(stored_orders) == 5

        stored_items = session.exec(select(ECommerceOrderItem)).all()
        assert len(stored_items) == 9

        stored_shipments = session.exec(select(ECommerceShipment)).all()
        assert len(stored_shipments) == 4

        stored_events = session.exec(select(ECommerceShipmentEvent)).all()
        assert len(stored_events) == 13

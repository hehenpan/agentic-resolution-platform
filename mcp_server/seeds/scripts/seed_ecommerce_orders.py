from __future__ import annotations

import logging
from loguru import logger
import pandas as pd
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from sqlmodel import Session, select

LOGGER = logging.getLogger(__name__)
MCP_ROOT = Path(__file__).resolve().parents[2]
MCP_SRC_DIR = MCP_ROOT / "src"

if str(MCP_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_SRC_DIR))

from core.database import get_session  # noqa: E402
from models.db_models import (  # noqa: E402
    ECommerceOrder,
    ECommerceOrderItem,
    ECommerceShipment,
    ECommerceShipmentEvent,
    OrderStatus,
    ShipmentStatus,
)
from common import parse_int_field, parse_float_field  # noqa: E402

DATA_DIR = MCP_ROOT / "seeds" / "data"
ORDERS_CSV = DATA_DIR / "ecommerce_orders.csv"
ORDER_ITEMS_CSV = DATA_DIR / "ecommerce_order_items.csv"
SHIPMENTS_CSV = DATA_DIR / "ecommerce_shipments.csv"
SHIPMENT_EVENTS_CSV = DATA_DIR / "ecommerce_shipment_events.csv"


@dataclass(frozen=True)
class OrderSeedRow:
    order_id: int
    user_id: int
    email: str
    status: OrderStatus
    total_amount: float
    created_ts: int


@dataclass(frozen=True)
class OrderItemSeedRow:
    item_id: int
    order_id: int
    sku_id: int
    sku_code: str
    name: str
    quantity: int
    price: float


@dataclass(frozen=True)
class ShipmentSeedRow:
    shipment_id: int
    order_id: int
    tracking_number: str
    carrier: str
    status: ShipmentStatus
    shipping_address: str
    created_ts: int
    updated_ts: int


@dataclass(frozen=True)
class ShipmentEventSeedRow:
    event_id: int
    shipment_id: int
    status: ShipmentStatus
    location: str
    description: str
    event_ts: int


@dataclass(frozen=True)
class OrderSeedResult:
    orders_inserted: int
    orders_updated: int
    items_inserted: int
    items_updated: int
    shipments_inserted: int
    shipments_updated: int
    events_inserted: int
    events_updated: int


SessionFactory = Callable[[], Iterator[Session]]


def load_orders(csv_path: Path = ORDERS_CSV) -> list[OrderSeedRow]:
    df = pd.read_csv(csv_path)
    required_cols = ["order_id", "user_id", "email", "status", "total_amount", "created_ts"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in orders CSV: {missing_cols}")
    df = df.dropna(subset=required_cols)

    rows: list[OrderSeedRow] = []
    for idx, row in df.iterrows():
        line = int(idx) + 2
        order_id = parse_int_field(row["order_id"], "order_id", line)
        user_id = parse_int_field(row["user_id"], "user_id", line)
        status_val = parse_int_field(row["status"], "status", line)
        total_amount = parse_float_field(row["total_amount"], "total_amount", line)
        created_ts = parse_int_field(row["created_ts"], "created_ts", line)

        rows.append(
            OrderSeedRow(
                order_id=order_id,
                user_id=user_id,
                email=str(row["email"]).strip(),
                status=OrderStatus(status_val),
                total_amount=total_amount,
                created_ts=created_ts,
            )
        )
    return rows


def load_order_items(csv_path: Path = ORDER_ITEMS_CSV) -> list[OrderItemSeedRow]:
    df = pd.read_csv(csv_path)
    required_cols = ["item_id", "order_id", "sku_id", "sku_code", "name", "quantity", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in order items CSV: {missing_cols}")
    df = df.dropna(subset=required_cols)

    rows: list[OrderItemSeedRow] = []
    for idx, row in df.iterrows():
        line = int(idx) + 2
        item_id = parse_int_field(row["item_id"], "item_id", line)
        order_id = parse_int_field(row["order_id"], "order_id", line)
        sku_id = parse_int_field(row["sku_id"], "sku_id", line)
        quantity = parse_int_field(row["quantity"], "quantity", line)
        price = parse_float_field(row["price"], "price", line)

        rows.append(
            OrderItemSeedRow(
                item_id=item_id,
                order_id=order_id,
                sku_id=sku_id,
                sku_code=str(row["sku_code"]).strip(),
                name=str(row["name"]).strip(),
                quantity=quantity,
                price=price,
            )
        )
    return rows


def load_shipments(csv_path: Path = SHIPMENTS_CSV) -> list[ShipmentSeedRow]:
    df = pd.read_csv(csv_path)
    required_cols = [
        "shipment_id",
        "order_id",
        "tracking_number",
        "carrier",
        "status",
        "shipping_address",
        "created_ts",
        "updated_ts",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in shipments CSV: {missing_cols}")
    df = df.dropna(subset=required_cols)

    rows: list[ShipmentSeedRow] = []
    for idx, row in df.iterrows():
        line = int(idx) + 2
        shipment_id = parse_int_field(row["shipment_id"], "shipment_id", line)
        order_id = parse_int_field(row["order_id"], "order_id", line)
        status_val = parse_int_field(row["status"], "status", line)
        created_ts = parse_int_field(row["created_ts"], "created_ts", line)
        updated_ts = parse_int_field(row["updated_ts"], "updated_ts", line)

        rows.append(
            ShipmentSeedRow(
                shipment_id=shipment_id,
                order_id=order_id,
                tracking_number=str(row["tracking_number"]).strip(),
                carrier=str(row["carrier"]).strip(),
                status=ShipmentStatus(status_val),
                shipping_address=str(row["shipping_address"]).strip(),
                created_ts=created_ts,
                updated_ts=updated_ts,
            )
        )
    return rows


def load_shipment_events(csv_path: Path = SHIPMENT_EVENTS_CSV) -> list[ShipmentEventSeedRow]:
    df = pd.read_csv(csv_path)
    required_cols = ["event_id", "shipment_id", "status", "location", "description", "event_ts"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in shipment events CSV: {missing_cols}")
    df = df.dropna(subset=required_cols)

    rows: list[ShipmentEventSeedRow] = []
    for idx, row in df.iterrows():
        line = int(idx) + 2
        event_id = parse_int_field(row["event_id"], "event_id", line)
        shipment_id = parse_int_field(row["shipment_id"], "shipment_id", line)
        status_val = parse_int_field(row["status"], "status", line)
        event_ts = parse_int_field(row["event_ts"], "event_ts", line)

        rows.append(
            ShipmentEventSeedRow(
                event_id=event_id,
                shipment_id=shipment_id,
                status=ShipmentStatus(status_val),
                location=str(row["location"]).strip(),
                description=str(row["description"]).strip(),
                event_ts=event_ts,
            )
        )
    return rows


def seed_ecommerce_orders(
    session_factory: SessionFactory = get_session,
) -> OrderSeedResult:
    orders = load_orders()
    items = load_order_items()
    shipments = load_shipments()
    events = load_shipment_events()

    orders_ins = orders_upd = 0
    items_ins = items_upd = 0
    shipments_ins = shipments_upd = 0
    events_ins = events_upd = 0

    try:
        with session_factory() as session:
            # 1. Seed Orders
            for o in orders:
                existing = session.get(ECommerceOrder, o.order_id)
                if existing is None:
                    session.add(
                        ECommerceOrder(
                            order_id=o.order_id,
                            user_id=o.user_id,
                            email=o.email,
                            status=o.status,
                            total_amount=o.total_amount,
                            created_ts=o.created_ts,
                        )
                    )
                    orders_ins += 1
                else:
                    existing.user_id = o.user_id
                    existing.email = o.email
                    existing.status = o.status
                    existing.total_amount = o.total_amount
                    existing.created_ts = o.created_ts
                    session.add(existing)
                    orders_upd += 1

            # 2. Seed Order Items
            for item in items:
                existing = session.get(ECommerceOrderItem, item.item_id)
                if existing is None:
                    session.add(
                        ECommerceOrderItem(
                            item_id=item.item_id,
                            order_id=item.order_id,
                            sku_id=item.sku_id,
                            sku_code=item.sku_code,
                            name=item.name,
                            quantity=item.quantity,
                            price=item.price,
                        )
                    )
                    items_ins += 1
                else:
                    existing.order_id = item.order_id
                    existing.sku_id = item.sku_id
                    existing.sku_code = item.sku_code
                    existing.name = item.name
                    existing.quantity = item.quantity
                    existing.price = item.price
                    session.add(existing)
                    items_upd += 1

            # 3. Seed Shipments
            for s in shipments:
                existing = session.get(ECommerceShipment, s.shipment_id)
                if existing is None:
                    session.add(
                        ECommerceShipment(
                            shipment_id=s.shipment_id,
                            order_id=s.order_id,
                            tracking_number=s.tracking_number,
                            carrier=s.carrier,
                            status=s.status,
                            shipping_address=s.shipping_address,
                            created_ts=s.created_ts,
                            updated_ts=s.updated_ts,
                        )
                    )
                    shipments_ins += 1
                else:
                    existing.order_id = s.order_id
                    existing.tracking_number = s.tracking_number
                    existing.carrier = s.carrier
                    existing.status = s.status
                    existing.shipping_address = s.shipping_address
                    existing.created_ts = s.created_ts
                    existing.updated_ts = s.updated_ts
                    session.add(existing)
                    shipments_upd += 1

            # 4. Seed Shipment Events
            for ev in events:
                existing = session.get(ECommerceShipmentEvent, ev.event_id)
                if existing is None:
                    session.add(
                        ECommerceShipmentEvent(
                            event_id=ev.event_id,
                            shipment_id=ev.shipment_id,
                            status=ev.status,
                            location=ev.location,
                            description=ev.description,
                            event_ts=ev.event_ts,
                        )
                    )
                    events_ins += 1
                else:
                    existing.shipment_id = ev.shipment_id
                    existing.status = ev.status
                    existing.location = ev.location
                    existing.description = ev.description
                    existing.event_ts = ev.event_ts
                    session.add(existing)
                    events_upd += 1

            session.commit()
    except Exception:
        logger.exception("Failed to seed ecommerce order and shipment data.")
        raise

    return OrderSeedResult(
        orders_inserted=orders_ins,
        orders_updated=orders_upd,
        items_inserted=items_ins,
        items_updated=items_upd,
        shipments_inserted=shipments_ins,
        shipments_updated=shipments_upd,
        events_inserted=events_ins,
        events_updated=events_upd,
    )


def main() -> None:
    res = seed_ecommerce_orders()
    logger.info(
        "Seeding completed. Orders: +{}/~{}, Items: +{}/~{}, Shipments: +{}/~{}, Events: +{}/~{}",
        res.orders_inserted,
        res.orders_updated,
        res.items_inserted,
        res.items_updated,
        res.shipments_inserted,
        res.shipments_updated,
        res.events_inserted,
        res.events_updated,
    )


if __name__ == "__main__":
    main()

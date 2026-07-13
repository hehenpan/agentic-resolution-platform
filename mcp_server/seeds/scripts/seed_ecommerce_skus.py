from __future__ import annotations

from loguru import logger
import pandas as pd
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from sqlmodel import Session, select
MCP_ROOT = Path(__file__).resolve().parents[2]
MCP_SRC_DIR = MCP_ROOT / "src"

if str(MCP_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_SRC_DIR))

from core.database import get_session  # noqa: E402
from models.db_models import ECommerceSKU  # noqa: E402
from common import parse_int_field, parse_float_field  # noqa: E402

DEFAULT_CSV_PATH = MCP_ROOT / "seeds" / "data" / "ecommerce_skus.csv"


@dataclass(frozen=True)
class ECommerceSKUSeedRow:
    sku_id: int
    sku_code: str
    name: str
    price: float
    stock: int
    description: str


@dataclass(frozen=True)
class SeedResult:
    inserted: int
    updated: int

    @property
    def processed(self) -> int:
        return self.inserted + self.updated


SessionFactory = Callable[[], Iterator[Session]]


def load_seed_rows(csv_path: Path = DEFAULT_CSV_PATH) -> list[ECommerceSKUSeedRow]:
    df = pd.read_csv(csv_path)
    
    # Check if all required columns exist in the DataFrame
    required_cols = ["sku_id", "sku_code", "name", "price", "stock"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        message = f"Missing required columns: {', '.join(missing_cols)}"
        logger.error(message)
        raise ValueError(message)


    # Drop any row containing NaN in the required columns
    df = df.dropna(subset=required_cols)

    rows: list[ECommerceSKUSeedRow] = []
    for idx, row in df.iterrows():
        line_number = int(idx) + 2
        sku_id_val = row["sku_id"]
        price_val = row["price"]
        stock_val = row["stock"]

        sku_id = parse_int_field(sku_id_val, "sku_id", line_number)
        price = parse_float_field(price_val, "price", line_number)
        stock = parse_int_field(stock_val, "stock", line_number)

        description = str(row["description"]).strip() if pd.notnull(row["description"]) else ""
        sku_code = str(row["sku_code"]).strip()
        name = str(row["name"]).strip()

        rows.append(
            ECommerceSKUSeedRow(
                sku_id=sku_id,
                sku_code=sku_code,
                name=name,
                price=price,
                stock=stock,
                description=description,
            )
        )

    return rows


def seed_ecommerce_skus(
    csv_path: Path = DEFAULT_CSV_PATH,
    session_factory: SessionFactory = get_session,
) -> SeedResult:
    rows = load_seed_rows(csv_path)
    inserted = 0
    updated = 0

    try:
        with session_factory() as session:
            for row in rows:
                existing = session.exec(
                    select(ECommerceSKU).where(ECommerceSKU.sku_code == row.sku_code)
                ).first()

                if existing is None:
                    session.add(
                        ECommerceSKU(
                            sku_id=row.sku_id,
                            sku_code=row.sku_code,
                            name=row.name,
                            price=row.price,
                            stock=row.stock,
                            description=row.description,
                        )
                    )
                    inserted += 1
                    continue

                existing.name = row.name
                existing.price = row.price
                existing.stock = row.stock
                existing.description = row.description
                session.add(existing)
                updated += 1
    except Exception:
        logger.exception("Failed to seed ecommerce SKU data from {}.", csv_path)
        raise

    return SeedResult(inserted=inserted, updated=updated)


def main() -> None:
    result = seed_ecommerce_skus()
    logger.info(
        "Seeded ecommerce SKUs from {}. inserted={} updated={} processed={}",
        DEFAULT_CSV_PATH,
        result.inserted,
        result.updated,
        result.processed,
    )


if __name__ == "__main__":
    main()

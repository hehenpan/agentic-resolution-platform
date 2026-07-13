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
from models.db_models import ECommerceUser  # noqa: E402
from common import parse_int_field  # noqa: E402

DEFAULT_CSV_PATH = MCP_ROOT / "seeds" / "data" / "ecommerce_users.csv"


@dataclass(frozen=True)
class ECommerceUserSeedRow:
    user_id: int
    user_name: str
    pwd: str
    email: str
    status: int
    phone: str
    create_ts: int


@dataclass(frozen=True)
class SeedResult:
    inserted: int
    updated: int

    @property
    def processed(self) -> int:
        return self.inserted + self.updated


SessionFactory = Callable[[], Iterator[Session]]


def load_seed_rows(csv_path: Path = DEFAULT_CSV_PATH) -> list[ECommerceUserSeedRow]:
    df = pd.read_csv(csv_path)
    
    # Check if all required columns exist in the DataFrame
    required_cols = ["user_id", "user_name", "pwd", "email", "status", "phone", "create_ts"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        message = f"Missing required columns: {', '.join(missing_cols)}"
        logger.error(message)
        raise ValueError(message)

    # Drop any row containing NaN in the required columns
    df = df.dropna(subset=required_cols)

    rows: list[ECommerceUserSeedRow] = []
    for idx, row in df.iterrows():
        line_number = int(idx) + 2
        user_id_val = row["user_id"]
        status_val = row["status"]
        create_ts_val = row["create_ts"]

        user_id = parse_int_field(user_id_val, "user_id", line_number)
        status = parse_int_field(status_val, "status", line_number)
        create_ts = parse_int_field(create_ts_val, "create_ts", line_number)

        user_name = str(row["user_name"]).strip()
        pwd = str(row["pwd"]).strip()
        email = str(row["email"]).strip()
        phone = str(row["phone"]).strip()

        rows.append(
            ECommerceUserSeedRow(
                user_id=user_id,
                user_name=user_name,
                pwd=pwd,
                email=email,
                status=status,
                phone=phone,
                create_ts=create_ts,
            )
        )

    return rows


def seed_ecommerce_users(
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
                    select(ECommerceUser).where(ECommerceUser.email == row.email)
                ).first()

                if existing is None:
                    session.add(
                        ECommerceUser(
                            user_id=row.user_id,
                            user_name=row.user_name,
                            pwd=row.pwd,
                            email=row.email,
                            status=row.status,
                            phone=row.phone,
                            create_ts=row.create_ts,
                        )
                    )
                    inserted += 1
                    continue

                existing.user_name = row.user_name
                existing.pwd = row.pwd
                existing.status = row.status
                existing.phone = row.phone
                existing.create_ts = row.create_ts
                session.add(existing)
                updated += 1
    except Exception:
        logger.exception("Failed to seed ecommerce user data from {}.", csv_path)
        raise

    return SeedResult(inserted=inserted, updated=updated)


def main() -> None:
    result = seed_ecommerce_users()
    logger.info(
        "Seeded ecommerce users from {}. inserted={} updated={} processed={}",
        DEFAULT_CSV_PATH,
        result.inserted,
        result.updated,
        result.processed,
    )


if __name__ == "__main__":
    main()

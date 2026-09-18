from __future__ import annotations

import enum
import hashlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from legacy_app.database import db
from legacy_app.models import (
    AuditEvent,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    User,
    UserRole,
)

SEED_TIME = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

IDS = {
    "customer": uuid.UUID("00000000-0000-4000-8000-000000000001"),
    "admin": uuid.UUID("00000000-0000-4000-8000-000000000002"),
    "inactive_user": uuid.UUID("00000000-0000-4000-8000-000000000003"),
    "widget": uuid.UUID("10000000-0000-4000-8000-000000000001"),
    "gadget": uuid.UUID("10000000-0000-4000-8000-000000000002"),
    "retired": uuid.UUID("10000000-0000-4000-8000-000000000003"),
    "order": uuid.UUID("20000000-0000-4000-8000-000000000001"),
    "order_item": uuid.UUID("30000000-0000-4000-8000-000000000001"),
    "payment": uuid.UUID("40000000-0000-4000-8000-000000000001"),
    "audit": uuid.UUID("50000000-0000-4000-8000-000000000001"),
}


def deterministic_password_hash(password: str, salt: str) -> str:
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2:sha256:{iterations}${salt}${digest}"


def seed_blueprint() -> dict[str, list[dict[str, Any]]]:
    """Return fresh, deterministic records suitable for insertion."""
    timestamp_fields = {"created_at": SEED_TIME, "updated_at": SEED_TIME}
    return {
        "users": [
            {
                "id": IDS["customer"],
                "email": "customer@example.com",
                "password_hash": deterministic_password_hash("customer-password", "customer-seed"),
                "role": UserRole.CUSTOMER,
                "active": True,
                **timestamp_fields,
            },
            {
                "id": IDS["admin"],
                "email": "admin@example.com",
                "password_hash": deterministic_password_hash("admin-password", "admin-seed"),
                "role": UserRole.ADMIN,
                "active": True,
                **timestamp_fields,
            },
            {
                "id": IDS["inactive_user"],
                "email": "inactive@example.com",
                "password_hash": deterministic_password_hash("inactive-password", "inactive-seed"),
                "role": UserRole.CUSTOMER,
                "active": False,
                **timestamp_fields,
            },
        ],
        "products": [
            {
                "id": IDS["widget"],
                "name": "Benchmark Widget",
                "description": "Active seeded product",
                "active": True,
                "unit_price": Decimal("19.90"),
                "currency": "USD",
                "inventory_quantity": 98,
                **timestamp_fields,
            },
            {
                "id": IDS["gadget"],
                "name": "Benchmark Gadget",
                "description": "Second active seeded product",
                "active": True,
                "unit_price": Decimal("5.25"),
                "currency": "USD",
                "inventory_quantity": 25,
                **timestamp_fields,
            },
            {
                "id": IDS["retired"],
                "name": "Retired Product",
                "description": "Inactive seeded product",
                "active": False,
                "unit_price": Decimal("7.00"),
                "currency": "USD",
                "inventory_quantity": 10,
                **timestamp_fields,
            },
        ],
        "orders": [
            {
                "id": IDS["order"],
                "user_id": IDS["customer"],
                "status": OrderStatus.PAID,
                "total_amount": Decimal("39.80"),
                "currency": "USD",
                **timestamp_fields,
            }
        ],
        "order_items": [
            {
                "id": IDS["order_item"],
                "order_id": IDS["order"],
                "product_id": IDS["widget"],
                "quantity": 2,
                "unit_price": Decimal("19.90"),
                **timestamp_fields,
            }
        ],
        "payments": [
            {
                "id": IDS["payment"],
                "order_id": IDS["order"],
                "status": PaymentStatus.AUTHORIZED,
                "amount": Decimal("39.80"),
                "currency": "USD",
                "provider_reference": "mock-seeded-authorization",
                "idempotency_key": "seed-order-0001",
                **timestamp_fields,
            }
        ],
        "audit_events": [
            {
                "id": IDS["audit"],
                "event_type": "order.created",
                "actor_user_id": IDS["customer"],
                "subject_type": "order",
                "subject_id": IDS["order"],
                "request_id": "seed-request-0001",
                "event_metadata": {"source": "deterministic-seed"},
                "created_at": SEED_TIME,
            }
        ],
    }


def seed_database() -> None:
    if db.session.scalar(select(User.id).limit(1)) is not None:
        return
    records = seed_blueprint()
    db.session.add_all(User(**values) for values in records["users"])
    db.session.add_all(Product(**values) for values in records["products"])
    db.session.flush()
    db.session.add_all(Order(**values) for values in records["orders"])
    db.session.flush()
    db.session.add_all(OrderItem(**values) for values in records["order_items"])
    db.session.add_all(Payment(**values) for values in records["payments"])
    db.session.add_all(AuditEvent(**values) for values in records["audit_events"])
    db.session.commit()


def reset_database() -> None:
    db.session.remove()
    db.drop_all()
    db.create_all()
    seed_database()


def database_snapshot() -> dict[str, list[dict[str, Any]]]:
    models = (User, Product, Order, OrderItem, Payment, AuditEvent)
    snapshot: dict[str, list[dict[str, Any]]] = {}
    for model in models:
        rows = db.session.scalars(select(model).order_by(model.id)).all()
        snapshot[model.__tablename__] = [
            {
                column.name: _json_value(getattr(row, column.key))
                for column in model.__table__.columns
            }
            for row in rows
        ]
    return snapshot


def snapshot_json() -> str:
    return json.dumps(database_snapshot(), sort_keys=True, separators=(",", ":"))


def _json_value(value: object) -> object:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (datetime, Decimal, uuid.UUID)):
        return str(value)
    return value

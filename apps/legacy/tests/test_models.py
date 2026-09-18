from __future__ import annotations

from sqlalchemy import CheckConstraint, Numeric, inspect

from legacy_app.database import db
from legacy_app.models import (
    AuditEvent,
    Order,
    OrderItem,
    Payment,
    Product,
    User,
)


def test_schema_contains_exactly_the_six_domain_entities() -> None:
    assert set(db.metadata.tables) == {
        "users",
        "products",
        "orders",
        "order_items",
        "payments",
        "audit_events",
    }


def test_money_columns_are_fixed_precision() -> None:
    for column in (
        Product.__table__.c.unit_price,
        Order.__table__.c.total_amount,
        OrderItem.__table__.c.unit_price,
        Payment.__table__.c.amount,
    ):
        assert isinstance(column.type, Numeric)
        assert column.type.precision == 12
        assert column.type.scale == 2


def test_timestamps_are_timezone_aware() -> None:
    timestamp_columns = (
        User.__table__.c.created_at,
        Product.__table__.c.updated_at,
        Order.__table__.c.created_at,
        OrderItem.__table__.c.updated_at,
        Payment.__table__.c.created_at,
        AuditEvent.__table__.c.created_at,
    )

    assert all(column.type.timezone is True for column in timestamp_columns)


def test_inventory_and_quantity_constraints_exist() -> None:
    product_checks = {
        constraint.name
        for constraint in Product.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    item_checks = {
        constraint.name
        for constraint in OrderItem.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_products_inventory_non_negative" in product_checks
    assert "ck_order_items_quantity_positive" in item_checks


def test_required_relationships_are_mapped() -> None:
    assert set(inspect(User).relationships.keys()) == {"orders"}
    assert set(inspect(Product).relationships.keys()) == {"order_items"}
    assert set(inspect(Order).relationships.keys()) == {"user", "items", "payment"}
    assert set(inspect(OrderItem).relationships.keys()) == {"order", "product"}
    assert set(inspect(Payment).relationships.keys()) == {"order"}
    assert set(inspect(AuditEvent).relationships.keys()) == {"actor"}

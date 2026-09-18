from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PythonEnum
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DDL,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from legacy_app.database import db


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserRole(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    FAILED = "failed"


def enum_type(enum_class: type[PythonEnum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(btrim(email))", name="normalized_email"),
        Index("ix_users_role_active", "role", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole, "user_role"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    orders: Mapped[list[Order]] = relationship(back_populates="user")


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("inventory_quantity >= 0", name="inventory_non_negative"),
        CheckConstraint(
            "currency = upper(currency) AND char_length(currency) = 3", name="currency"
        ),
        Index("ix_products_active_id", "active", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    inventory_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order_items: Mapped[list[OrderItem]] = relationship(back_populates="product")


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="total_non_negative"),
        CheckConstraint(
            "currency = upper(currency) AND char_length(currency) = 3", name="currency"
        ),
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        enum_type(OrderStatus, "order_status"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payment: Mapped[Payment | None] = relationship(
        back_populates="order", cascade="all, delete-orphan", uselist=False
    )


class OrderItem(TimestampMixin, db.Model):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        Index("ix_order_items_product", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint(
            "currency = upper(currency) AND char_length(currency) = 3", name="currency"
        ),
        Index("ix_payments_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        enum_type(PaymentStatus, "payment_status"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(255), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    order: Mapped[Order] = relationship(back_populates="payment")


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_type_created", "event_type", "created_at"),
        Index("ix_audit_events_subject", "subject_type", "subject_id"),
        Index("ix_audit_events_request_id", "request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    actor: Mapped[User | None] = relationship()


@event.listens_for(OrderItem, "before_update", propagate=True)
def prevent_captured_price_update(_mapper: object, _connection: object, target: OrderItem) -> None:
    history = inspect(target).attrs.unit_price.history
    if history.has_changes():
        raise ValueError("captured OrderItem.unit_price is immutable")


@event.listens_for(AuditEvent, "before_update", propagate=True)
@event.listens_for(AuditEvent, "before_delete", propagate=True)
def prevent_audit_mutation(_mapper: object, _connection: object, _target: AuditEvent) -> None:
    raise ValueError("AuditEvent rows are append-only")


# PostgreSQL triggers also protect these invariants from writes that bypass the ORM.
event.listen(
    OrderItem.__table__,
    "after_create",
    DDL(
        """
        CREATE FUNCTION prevent_order_item_price_change() RETURNS trigger AS $$
        BEGIN
            IF NEW.unit_price IS DISTINCT FROM OLD.unit_price THEN
                RAISE EXCEPTION 'captured order item price is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    OrderItem.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER trg_order_item_price_immutable
        BEFORE UPDATE ON order_items
        FOR EACH ROW EXECUTE FUNCTION prevent_order_item_price_change()
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    OrderItem.__table__,
    "after_drop",
    DDL("DROP FUNCTION IF EXISTS prevent_order_item_price_change()").execute_if(
        dialect="postgresql"
    ),
)
event.listen(
    AuditEvent.__table__,
    "after_create",
    DDL(
        """
        CREATE FUNCTION prevent_audit_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER trg_audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation()
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "after_drop",
    DDL("DROP FUNCTION IF EXISTS prevent_audit_event_mutation()").execute_if(dialect="postgresql"),
)

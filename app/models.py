from __future__ import annotations

from datetime import date, datetime, timezone
UTC = timezone.utc
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


Money = Numeric(12, 2)
Area = Numeric(12, 2)


class PropertyObject(Base):
    __tablename__ = "property_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    total_area: Mapped[Decimal] = mapped_column(Area, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    placements: Mapped[List["LeasePlacement"]] = relationship(back_populates="object")
    charges: Mapped[List["UtilityCharge"]] = relationship(back_populates="object")
    rules: Mapped[List["AllocationRule"]] = relationship(back_populates="object")
    tariffs: Mapped[List["Tariff"]] = relationship(back_populates="object")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    note: Mapped[Optional[str]] = mapped_column(Text())
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    placements: Mapped[List["LeasePlacement"]] = relationship(back_populates="tenant")
    rules: Mapped[List["AllocationRule"]] = relationship(back_populates="tenant")
    payments: Mapped[List["TenantPayment"]] = relationship(back_populates="tenant")


class LeasePlacement(Base):
    __tablename__ = "lease_placements"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("property_objects.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    rental_address: Mapped[str] = mapped_column(String(255), nullable=False)
    occupied_area: Mapped[Decimal] = mapped_column(Area, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    rent_tariff: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="active")
    comment: Mapped[Optional[str]] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    object: Mapped[PropertyObject] = relationship(back_populates="placements")
    tenant: Mapped[Tenant] = relationship(back_populates="placements")
    allocations: Mapped[List["ChargeAllocation"]] = relationship(back_populates="placement")


class BillingPeriod(Base):
    __tablename__ = "billing_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)
    month_label: Mapped[Optional[str]] = mapped_column(String(7))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    charges: Mapped[List["UtilityCharge"]] = relationship(back_populates="billing_period")
    allocations: Mapped[List["ChargeAllocation"]] = relationship(back_populates="billing_period")
    documents: Mapped[List["GeneratedDocument"]] = relationship(back_populates="billing_period")


class UtilityCharge(Base):
    __tablename__ = "utility_charges"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("property_objects.id"), nullable=False)
    billing_period_id: Mapped[int] = mapped_column(ForeignKey("billing_periods.id"), nullable=False)
    utility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    input_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    allocation_mode: Mapped[str] = mapped_column(String(20), default="area")
    amount: Mapped[Optional[Decimal]] = mapped_column(Money)
    meter_from: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    meter_to: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    tariff: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    unit_name: Mapped[Optional[str]] = mapped_column(String(30))
    comment: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    object: Mapped[PropertyObject] = relationship(back_populates="charges")
    billing_period: Mapped[BillingPeriod] = relationship(back_populates="charges")
    allocations: Mapped[List["ChargeAllocation"]] = relationship(back_populates="utility_charge")


class AllocationRule(Base):
    __tablename__ = "allocation_rules"
    __table_args__ = (
        UniqueConstraint("object_id", "utility_type", "tenant_id", name="uq_rule_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("property_objects.id"), nullable=False)
    utility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="area")
    base_area_mode: Mapped[str] = mapped_column(String(20), default="active_leases")
    tenant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tenants.id"))
    value_type: Mapped[Optional[str]] = mapped_column(String(20))
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    object: Mapped[PropertyObject] = relationship(back_populates="rules")
    tenant: Mapped[Optional[Tenant]] = relationship(back_populates="rules")


class ChargeAllocation(Base):
    __tablename__ = "charge_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    billing_period_id: Mapped[int] = mapped_column(ForeignKey("billing_periods.id"), nullable=False)
    utility_charge_id: Mapped[Optional[int]] = mapped_column(ForeignKey("utility_charges.id"), nullable=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("property_objects.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    placement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lease_placements.id"), nullable=True)
    base_area: Mapped[Decimal] = mapped_column(Area, nullable=False, default=0)
    share_value: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    audit_payload: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    billing_period: Mapped[BillingPeriod] = relationship(back_populates="allocations")
    utility_charge: Mapped[Optional[UtilityCharge]] = relationship(back_populates="allocations")
    object: Mapped[PropertyObject] = relationship()
    tenant: Mapped[Tenant] = relationship()
    placement: Mapped[Optional[LeasePlacement]] = relationship(back_populates="allocations")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    billing_period_id: Mapped[int] = mapped_column(ForeignKey("billing_periods.id"), nullable=False)
    tenant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tenants.id"))
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    billing_period: Mapped[BillingPeriod] = relationship(back_populates="documents")
    tenant: Mapped[Optional[Tenant]] = relationship()


class TrashBin(Base):
    __tablename__ = "trash_bin"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_id: Mapped[int] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_json: Mapped[str] = mapped_column(Text(), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("property_objects.id"), nullable=False)
    tenant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    utility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_name: Mapped[Optional[str]] = mapped_column(String(30))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    object: Mapped[PropertyObject] = relationship(back_populates="tariffs")
    tenant: Mapped[Optional[Tenant]] = relationship()


class TenantPayment(Base):
    __tablename__ = "tenant_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    billing_period_id: Mapped[int] = mapped_column(ForeignKey("billing_periods.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, default=lambda: date.today())
    comment: Mapped[Optional[str]] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    tenant: Mapped[Tenant] = relationship(back_populates="payments")
    billing_period: Mapped[BillingPeriod] = relationship()



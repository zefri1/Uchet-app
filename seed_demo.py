from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.db import SessionLocal
from app.models import BillingPeriod, LeasePlacement, PropertyObject, Tenant, UtilityCharge


def main():
    db = SessionLocal()
    try:
        if db.query(PropertyObject).count():
            print("Demo data already exists.")
            return

        obj = PropertyObject(name="БЦ Север", address="Москва, ул. Примерная, 1", total_area=Decimal("120"))
        tenant_a = Tenant(tenant_type="ООО", display_name="Альфа", phone="+7 900 100 00 01")
        tenant_b = Tenant(tenant_type="ИП", display_name="Бета", phone="+7 900 100 00 02")
        period = BillingPeriod(period_type="month", month_label="2026-06", start_date=date(2026, 6, 1), end_date=date(2026, 6, 30))
        db.add_all([obj, tenant_a, tenant_b, period])
        db.commit()

        db.add_all(
            [
                LeasePlacement(
                    object_id=obj.id,
                    tenant_id=tenant_a.id,
                    rental_address=obj.address,
                    occupied_area=Decimal("70"),
                    start_date=date(2026, 1, 1),
                    is_active=True,
                ),
                LeasePlacement(
                    object_id=obj.id,
                    tenant_id=tenant_b.id,
                    rental_address=obj.address,
                    occupied_area=Decimal("30"),
                    start_date=date(2026, 1, 1),
                    is_active=True,
                ),
                UtilityCharge(
                    object_id=obj.id,
                    billing_period_id=period.id,
                    utility_type="heat",
                    input_mode="amount",
                    allocation_mode="area",
                    amount=Decimal("15000"),
                    comment="Тестовый счет за тепло",
                ),
                UtilityCharge(
                    object_id=obj.id,
                    billing_period_id=period.id,
                    utility_type="electricity",
                    input_mode="meter",
                    allocation_mode="mixed",
                    meter_from=Decimal("1200"),
                    meter_to=Decimal("1475"),
                    tariff=Decimal("6.10"),
                    unit_name="кВт⋅ч",
                    comment="Тестовый счет за электроэнергию",
                ),
            ]
        )
        db.commit()
        print("Demo data created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

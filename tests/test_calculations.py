from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import AllocationRule, BillingPeriod, ChargeAllocation, LeasePlacement, PropertyObject, Tenant, UtilityCharge
from app.services.calculations import get_charge_amount, recalculate_period


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.db: Session = self.Session()

        obj = PropertyObject(name="БЦ Север", address="Москва", total_area=Decimal("100"))
        tenant_a = Tenant(tenant_type="ООО", display_name="Альфа")
        tenant_b = Tenant(tenant_type="ИП", display_name="Бета")
        period = BillingPeriod(period_type="month", month_label="2026-06", start_date=date(2026, 6, 1), end_date=date(2026, 6, 30))
        self.db.add_all([obj, tenant_a, tenant_b, period])
        self.db.commit()
        self.obj_id = obj.id
        self.tenant_a_id = tenant_a.id
        self.tenant_b_id = tenant_b.id
        self.period_id = period.id

        self.db.add_all(
            [
                LeasePlacement(
                    object_id=obj.id,
                    tenant_id=tenant_a.id,
                    rental_address="Москва",
                    occupied_area=Decimal("60"),
                    start_date=date(2026, 1, 1),
                    is_active=True,
                ),
                LeasePlacement(
                    object_id=obj.id,
                    tenant_id=tenant_b.id,
                    rental_address="Москва",
                    occupied_area=Decimal("40"),
                    start_date=date(2026, 1, 1),
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_meter_charge_amount(self):
        charge = UtilityCharge(
            object_id=self.obj_id,
            billing_period_id=self.period_id,
            utility_type="electricity",
            input_mode="meter",
            allocation_mode="area",
            meter_from=Decimal("100"),
            meter_to=Decimal("145"),
            tariff=Decimal("6.2"),
        )
        self.assertEqual(get_charge_amount(charge), Decimal("279.00"))

    def test_area_allocation(self):
        self.db.add(
            UtilityCharge(
                object_id=self.obj_id,
                billing_period_id=self.period_id,
                utility_type="heat",
                input_mode="amount",
                allocation_mode="area",
                amount=Decimal("1000"),
            )
        )
        self.db.commit()
        recalculate_period(self.db, self.period_id)
        allocations = self.db.query(ChargeAllocation).all()
        amounts = sorted(Decimal(item.amount) for item in allocations)
        self.assertEqual(amounts, [Decimal("400.00"), Decimal("600.00")])

    def test_mixed_mode_manual_percent(self):
        self.db.add(
            AllocationRule(
                object_id=self.obj_id,
                utility_type="water",
                mode="mixed",
                base_area_mode="active_leases",
                tenant_id=self.tenant_b_id,
                value_type="percent",
                value=Decimal("25"),
            )
        )
        self.db.add(
            UtilityCharge(
                object_id=self.obj_id,
                billing_period_id=self.period_id,
                utility_type="water",
                input_mode="amount",
                allocation_mode="mixed",
                amount=Decimal("800"),
            )
        )
        self.db.commit()
        recalculate_period(self.db, self.period_id)
        allocations = self.db.query(ChargeAllocation).filter_by(billing_period_id=self.period_id).all()
        by_tenant = {item.tenant_id: Decimal(item.amount) for item in allocations}
        self.assertEqual(by_tenant[self.tenant_b_id], Decimal("200.00"))
        self.assertEqual(by_tenant[self.tenant_a_id], Decimal("600.00"))

    def test_object_total_base_area_mode(self):
        self.db.add(
            AllocationRule(
                object_id=self.obj_id,
                utility_type="cleaning",
                mode="area",
                base_area_mode="object_total",
            )
        )
        self.db.add(
            UtilityCharge(
                object_id=self.obj_id,
                billing_period_id=self.period_id,
                utility_type="cleaning",
                input_mode="amount",
                allocation_mode="area",
                amount=Decimal("1000"),
            )
        )
        self.db.commit()
        recalculate_period(self.db, self.period_id)
        allocations = self.db.query(ChargeAllocation).filter_by(billing_period_id=self.period_id).all()
        by_tenant = {item.tenant_id: Decimal(item.amount) for item in allocations}
        self.assertEqual(by_tenant[self.tenant_a_id], Decimal("600.00"))
        self.assertEqual(by_tenant[self.tenant_b_id], Decimal("400.00"))

    def test_rent_calculation_full_month(self):
        # Set rent_tariff on placement of Tenant A
        placement_a = self.db.query(LeasePlacement).filter_by(tenant_id=self.tenant_a_id).first()
        placement_a.rent_tariff = Decimal("800.00")
        self.db.commit()

        recalculate_period(self.db, self.period_id)

        # There should be a rent allocation (utility_charge_id is None)
        rent_alloc = self.db.query(ChargeAllocation).filter_by(
            billing_period_id=self.period_id,
            tenant_id=self.tenant_a_id,
            utility_charge_id=None
        ).first()

        self.assertIsNotNone(rent_alloc)
        # occupied_area = 60, tariff = 800, active_days = 30, days_in_month = 30
        # 60 * 800 * 30 / 30 = 48000
        self.assertEqual(Decimal(rent_alloc.amount), Decimal("48000.00"))

    def test_rent_calculation_partial_month(self):
        # Create a new placement for Tenant B starting from mid-period (16th June to 30th June = 15 days)
        # Period 2026-06 is 30 days
        new_placement = LeasePlacement(
            object_id=self.obj_id,
            tenant_id=self.tenant_b_id,
            rental_address="Офис 102",
            occupied_area=Decimal("30"),
            start_date=date(2026, 6, 16),
            rent_tariff=Decimal("800.00"),
            is_active=True
        )
        # Deactivate previous placement of Tenant B to avoid collision
        old_placement = self.db.query(LeasePlacement).filter_by(tenant_id=self.tenant_b_id, is_active=True).first()
        old_placement.is_active = False
        
        self.db.add(new_placement)
        self.db.commit()

        recalculate_period(self.db, self.period_id)

        rent_alloc = self.db.query(ChargeAllocation).filter_by(
            billing_period_id=self.period_id,
            tenant_id=self.tenant_b_id,
            utility_charge_id=None
        ).first()

        self.assertIsNotNone(rent_alloc)
        # occupied_area = 30, tariff = 800, active_days = 15, period_days = 30
        # 30 * 800 * 15 / 30 = 12000
        self.assertEqual(Decimal(rent_alloc.amount), Decimal("12000.00"))

    def test_utility_calculation_by_tariff(self):
        # Setup rent tariff on placement of Tenant A to keep it valid
        placement_a = self.db.query(LeasePlacement).filter_by(tenant_id=self.tenant_a_id).first()
        placement_a.rent_tariff = Decimal("800.00")
        
        # Add tariff-based utility charge for electricity
        self.db.add(
            UtilityCharge(
                object_id=self.obj_id,
                billing_period_id=self.period_id,
                utility_type="electricity",
                input_mode="tariff",
                allocation_mode="area",
                tariff=Decimal("50.00"), # 50 руб/м2
            )
        )
        self.db.commit()
        recalculate_period(self.db, self.period_id)

        # Check electricity allocations (input_mode == tariff)
        allocations = self.db.query(ChargeAllocation).filter(ChargeAllocation.utility_charge_id.isnot(None)).all()
        # Tenant A occupied 60 m2, Tenant B occupied 40 m2
        # Tenant A electricity = 60 * 50 = 3000
        # Tenant B electricity = 40 * 50 = 2000 (skipped rent because rent_tariff is None, but utility has tariff=50)
        by_tenant = {item.tenant_id: Decimal(item.amount) for item in allocations if item.utility_charge.utility_type == "electricity"}
        self.assertEqual(by_tenant[self.tenant_a_id], Decimal("3000.00"))
        self.assertEqual(by_tenant[self.tenant_b_id], Decimal("2000.00"))

    def test_lump_sum_allocation_by_occupied_area_with_partial_month(self):
        # Make Tenant B active for only 15 days (occupied_area = 40)
        placement_b = self.db.query(LeasePlacement).filter_by(tenant_id=self.tenant_b_id).first()
        placement_b.start_date = date(2026, 6, 16)
        
        # Tenant A is active for 30 days (occupied_area = 60)
        # Weight A = 60 * 30/30 = 60
        # Weight B = 40 * 15/30 = 20
        # Total Weight = 80
        # Charge amount = 8000
        # Tenant A allocation = 8000 * 60/80 = 6000
        # Tenant B allocation = 8000 * 20/80 = 2000
        self.db.add(
            UtilityCharge(
                object_id=self.obj_id,
                billing_period_id=self.period_id,
                utility_type="heat",
                input_mode="amount",
                allocation_mode="area",
                amount=Decimal("8000"),
            )
        )
        self.db.commit()
        recalculate_period(self.db, self.period_id)

        allocations = self.db.query(ChargeAllocation).filter(ChargeAllocation.utility_charge_id.isnot(None)).all()
        by_tenant = {item.tenant_id: Decimal(item.amount) for item in allocations if item.utility_charge.utility_type == "heat"}
        self.assertEqual(by_tenant[self.tenant_a_id], Decimal("6000.00"))
        self.assertEqual(by_tenant[self.tenant_b_id], Decimal("2000.00"))


if __name__ == "__main__":
    unittest.main()

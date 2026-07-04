import unittest
from datetime import date, datetime, timezone
UTC = timezone.utc
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Tenant, BillingPeriod, TenantPayment, ChargeAllocation, PropertyObject
from app.main import get_tenant_balances

class TestPayments(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_balances_calculation(self):
        # Create periods
        p1 = BillingPeriod(
            period_type="month",
            month_label="2026-05",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
            status="draft"
        )
        p2 = BillingPeriod(
            period_type="month",
            month_label="2026-06",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            status="draft"
        )
        self.db.add_all([p1, p2])
        self.db.commit()

        # Create tenant with initial balance
        t = Tenant(
            tenant_type="ИП",
            display_name="Тестовый Арендатор",
            phone="123",
            initial_balance=Decimal("1000.00")
        )
        self.db.add(t)
        self.db.commit()

        # Create property object
        obj = PropertyObject(
            name="Здание 1",
            address="Адрес 1",
            total_area=Decimal("100.00")
        )
        self.db.add(obj)
        self.db.commit()

        # Allocations in period 1
        alloc1 = ChargeAllocation(
            billing_period_id=p1.id,
            object_id=obj.id,
            tenant_id=t.id,
            base_area=Decimal("10.00"),
            amount=Decimal("5000.00"),
            mode="area"
        )
        self.db.add(alloc1)
        self.db.commit()

        # Payments in period 1
        pay1 = TenantPayment(
            tenant_id=t.id,
            billing_period_id=p1.id,
            amount=Decimal("4000.00"),
            payment_date=date(2026, 5, 15)
        )
        self.db.add(pay1)
        self.db.commit()

        # Balance at the end of period 1
        # Incoming: 1000 (initial)
        # Allocated: 5000
        # Paid: 4000
        # Outgoing: 1000 + 5000 - 4000 = 2000
        b1 = get_tenant_balances(self.db, p1)
        self.assertEqual(b1[t.id]["incoming"], Decimal("1000.00"))
        self.assertEqual(b1[t.id]["allocated"], Decimal("5000.00"))
        self.assertEqual(b1[t.id]["paid"], Decimal("4000.00"))
        self.assertEqual(b1[t.id]["outgoing"], Decimal("2000.00"))

        # Allocations and payments in period 2
        alloc2 = ChargeAllocation(
            billing_period_id=p2.id,
            object_id=obj.id,
            tenant_id=t.id,
            base_area=Decimal("10.00"),
            amount=Decimal("7000.00"),
            mode="area"
        )
        pay2 = TenantPayment(
            tenant_id=t.id,
            billing_period_id=p2.id,
            amount=Decimal("9000.00"),
            payment_date=date(2026, 6, 15)
        )
        self.db.add_all([alloc2, pay2])
        self.db.commit()

        # Balance at the end of period 2
        # Incoming: 2000 (outgoing of p1)
        # Allocated: 7000
        # Paid: 9000
        # Outgoing: 2000 + 7000 - 9000 = 0
        b2 = get_tenant_balances(self.db, p2)
        self.assertEqual(b2[t.id]["incoming"], Decimal("2000.00"))
        self.assertEqual(b2[t.id]["allocated"], Decimal("7000.00"))
        self.assertEqual(b2[t.id]["paid"], Decimal("9000.00"))
        self.assertEqual(b2[t.id]["outgoing"], Decimal("0.00"))

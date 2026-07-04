from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.models import (
    PropertyObject, Tenant, BillingPeriod, LeasePlacement,
    UtilityCharge, ChargeAllocation, Tariff, TrashBin
)
from app.services.calculations import recalculate_period
from app.services.documents import (
    generate_invoice_docx, generate_act_docx,
    generate_register_xlsx, generate_invoice_xlsx, generate_act_xlsx
)

class SystemVerifier(unittest.TestCase):
    def setUp(self):
        # Create clean in-memory database for testing
        self.engine = create_engine(
            "sqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def test_step_1_db_schema(self):
        print("Running STEP 1: DB Schema Verification...")
        inspector = inspect(self.engine)
        
        # 1.1 Verify tariffs table exists
        self.assertIn("tariffs", inspector.get_table_names(), "Table 'tariffs' is missing!")
        print("  - [OK] Table 'tariffs' exists.")
        
        # 1.2 Verify lease_placements columns
        lp_cols = {col["name"]: col["type"] for col in inspector.get_columns("lease_placements")}
        self.assertIn("rent_tariff", lp_cols, "Column 'rent_tariff' in 'lease_placements' is missing!")
        self.assertIn("status", lp_cols, "Column 'status' in 'lease_placements' is missing!")
        self.assertIn("comment", lp_cols, "Column 'comment' in 'lease_placements' is missing!")
        print("  - [OK] Table 'lease_placements' has new columns: rent_tariff, status, comment.")

        # 1.3 Verify charge_allocations columns
        ca_cols = {col["name"]: col["type"] for col in inspector.get_columns("charge_allocations")}
        self.assertIn("placement_id", ca_cols, "Column 'placement_id' in 'charge_allocations' is missing!")
        print("  - [OK] Table 'charge_allocations' has column: placement_id.")

    def test_step_2_calculations_logic(self):
        print("Running STEP 2: Calculations Logic Verification...")
        with self.Session() as db:
            # 2.1 Seed property object and tenants
            obj = PropertyObject(name="БЦ Весна", address="Ул. Мира, 1", total_area=Decimal("150"))
            tenant_a = Tenant(tenant_type="ООО", display_name="Ромашка", phone="111")
            tenant_b = Tenant(tenant_type="ИП", display_name="Смирнов", phone="222")
            period = BillingPeriod(
                period_type="month",
                month_label="2026-06",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 30),
            )
            db.add_all([obj, tenant_a, tenant_b, period])
            db.commit()

            obj_id, ta_id, tb_id, p_id = obj.id, tenant_a.id, tenant_b.id, period.id

            # 2.2 Placement A: Active full month (30 days), Area = 60, Rent tariff = 800
            placement_a = LeasePlacement(
                object_id=obj_id,
                tenant_id=ta_id,
                rental_address="Офис 101",
                occupied_area=Decimal("60"),
                start_date=date(2026, 6, 1),
                rent_tariff=Decimal("800"),
                is_active=True,
                status="active"
            )
            # Placement B: Active half month (15 days), Area = 40, Rent tariff = 800
            placement_b = LeasePlacement(
                object_id=obj_id,
                tenant_id=tb_id,
                rental_address="Офис 102",
                occupied_area=Decimal("40"),
                start_date=date(2026, 6, 16),
                rent_tariff=Decimal("800"),
                is_active=True,
                status="active"
            )
            db.add_all([placement_a, placement_b])
            db.commit()

            # 2.3 Run Recalculate Period for Rent
            recalculate_period(db, p_id)

            # Check rent allocations
            rent_a = db.query(ChargeAllocation).filter_by(billing_period_id=p_id, tenant_id=ta_id, utility_charge_id=None).first()
            rent_b = db.query(ChargeAllocation).filter_by(billing_period_id=p_id, tenant_id=tb_id, utility_charge_id=None).first()
            
            self.assertIsNotNone(rent_a)
            self.assertIsNotNone(rent_b)
            
            # Rent A: 60 * 800 * 30/30 = 48000
            self.assertEqual(Decimal(rent_a.amount), Decimal("48000.00"))
            # Rent B: 40 * 800 * 15/30 = 16000
            self.assertEqual(Decimal(rent_b.amount), Decimal("16000.00"))
            print("  - [OK] Rent calculation (active area * tariff * active days) verified successfully.")

            # 2.4 Test Utility by Tariff (electricity: tariff = 50)
            charge_tariff = UtilityCharge(
                object_id=obj_id,
                billing_period_id=p_id,
                utility_type="electricity",
                input_mode="tariff",
                allocation_mode="area",
                tariff=Decimal("50")
            )
            db.add(charge_tariff)
            db.commit()

            recalculate_period(db, p_id)
            
            util_a = db.query(ChargeAllocation).filter_by(billing_period_id=p_id, tenant_id=ta_id, utility_charge_id=charge_tariff.id).first()
            util_b = db.query(ChargeAllocation).filter_by(billing_period_id=p_id, tenant_id=tb_id, utility_charge_id=charge_tariff.id).first()
            
            # Util A: 60 * 50 * 30/30 = 3000
            self.assertEqual(Decimal(util_a.amount), Decimal("3000.00"))
            # Util B: 40 * 50 * 15/30 = 1000
            self.assertEqual(Decimal(util_b.amount), Decimal("1000.00"))
            print("  - [OK] Utility calculation by tariff verified successfully.")

            # 2.5 Test Lump Sum distribution (heat: total = 8000)
            charge_lump = UtilityCharge(
                object_id=obj_id,
                billing_period_id=p_id,
                utility_type="heat",
                input_mode="amount",
                allocation_mode="area",
                amount=Decimal("8000")
            )
            db.add(charge_lump)
            db.commit()

            recalculate_period(db, p_id)

            lump_a = db.query(ChargeAllocation).filter_by(billing_period_id=p_id, tenant_id=ta_id, utility_charge_id=charge_lump.id).first()
            lump_b = db.query(ChargeAllocation).filter_by(billing_period_id=p_id, tenant_id=tb_id, utility_charge_id=charge_lump.id).first()
            
            # Total weight = (60 * 30/30) + (40 * 15/30) = 60 + 20 = 80
            # Lump A: 8000 * 60 / 80 = 6000
            self.assertEqual(Decimal(lump_a.amount), Decimal("6000.00"))
            # Lump B: 8000 * 20 / 80 = 2000
            self.assertEqual(Decimal(lump_b.amount), Decimal("2000.00"))
            print("  - [OK] Lump sum allocation based on time-area weights verified successfully.")

    def test_step_3_api_endpoints(self):
        print("Running STEP 3: API Endpoints Verification...")
        # 3.1 Setup prerequisite data
        with self.Session() as db:
            obj = PropertyObject(name="БЦ Весна", address="Ул. Мира, 1", total_area=Decimal("150"))
            tenant = Tenant(tenant_type="ООО", display_name="Ромашка", phone="111")
            db.add_all([obj, tenant])
            db.commit()
            obj_id = obj.id
            tenant_id = tenant.id

        # 3.2 Verify Placement Creation with rent_tariff, status, comment
        response = self.client.post(
            "/placements",
            data={
                "object_id": obj_id,
                "tenant_id": tenant_id,
                "rental_address": "Офис 101",
                "occupied_area": "50",
                "start_date": "2026-06-01",
                "is_active": "on",
                "rent_tariff": "750",
                "status": "active",
                "comment": "Тестовое примечание"
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            placement = db.query(LeasePlacement).first()
            self.assertIsNotNone(placement)
            self.assertEqual(placement.rent_tariff, Decimal("750.00"))
            self.assertEqual(placement.status, "active")
            self.assertEqual(placement.comment, "Тестовое примечание")
            print("  - [OK] POST /placements endpoint successfully saves new fields.")

        # 3.3 Verify Tariff Creation via API
        response = self.client.post(
            "/tariffs",
            data={
                "object_id": obj_id,
                "tenant_id": str(tenant_id),
                "utility_type": "water",
                "value": "45.50",
                "unit_name": "руб./м3",
                "start_date": "2026-06-01",
                "is_active": "on"
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            tariff = db.query(Tariff).first()
            self.assertIsNotNone(tariff)
            self.assertEqual(tariff.value, Decimal("45.50"))
            self.assertEqual(tariff.utility_type, "water")
            print("  - [OK] POST /tariffs endpoint successfully registers new tariffs.")

    def test_step_4_documents_generation(self):
        print("Running STEP 4: Document Generation Verification...")
        with self.Session() as db:
            obj = PropertyObject(name="БЦ Весна", address="Ул. Мира, 1", total_area=Decimal("150"))
            tenant = Tenant(tenant_type="ООО", display_name="Ромашка", phone="111")
            period = BillingPeriod(
                period_type="month",
                month_label="2026-06",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 30),
            )
            db.add_all([obj, tenant, period])
            db.commit()

            placement = LeasePlacement(
                object_id=obj.id,
                tenant_id=tenant.id,
                rental_address="Офис 101",
                occupied_area=Decimal("60"),
                start_date=date(2026, 6, 1),
                rent_tariff=Decimal("800"),
                is_active=True
            )
            db.add(placement)
            db.commit()

            recalculate_period(db, period.id)

            # Generate documents
            try:
                inv_docx = generate_invoice_docx(db, period, tenant)
                self.assertTrue(Path(inv_docx.file_path).exists())
                os.remove(inv_docx.file_path)
                print("  - [OK] Word Invoice document generated successfully.")

                act_docx = generate_act_docx(db, period, tenant)
                self.assertTrue(Path(act_docx.file_path).exists())
                os.remove(act_docx.file_path)
                print("  - [OK] Word Act document generated successfully.")

                inv_xlsx = generate_invoice_xlsx(db, period, tenant)
                self.assertTrue(Path(inv_xlsx.file_path).exists())
                os.remove(inv_xlsx.file_path)
                print("  - [OK] Excel Invoice document generated successfully.")

                act_xlsx = generate_act_xlsx(db, period, tenant)
                self.assertTrue(Path(act_xlsx.file_path).exists())
                os.remove(act_xlsx.file_path)
                print("  - [OK] Excel Act document generated successfully.")
            except Exception as e:
                self.fail(f"Document generation raised exception: {e}")

if __name__ == "__main__":
    unittest.main()

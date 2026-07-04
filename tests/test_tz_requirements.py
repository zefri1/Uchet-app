from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import BillingPeriod, PropertyObject, Tenant


class TzRequirementTests(unittest.TestCase):
    def setUp(self):
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

    def test_limit_10_objects(self):
        for idx in range(10):
            response = self.client.post(
                "/objects",
                data={"name": f"Объект {idx}", "address": f"Адрес {idx}", "total_area": "100"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)

        response = self.client.post(
            "/objects",
            data={"name": "Лишний", "address": "Адрес", "total_area": "100"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("10 объектов", response.text)

    def test_limit_50_tenants(self):
        for idx in range(50):
            response = self.client.post(
                "/tenants",
                data={"tenant_type": "ООО", "display_name": f"Tenant {idx}", "phone": "123"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)

        response = self.client.post(
            "/tenants",
            data={"tenant_type": "ИП", "display_name": "Лишний", "phone": "123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("50 арендаторов", response.text)

    def test_required_tz_fields_and_binding(self):
        with self.Session() as db:
            obj = PropertyObject(name="БЦ", address="Москва", total_area=Decimal("150"))
            tenant = Tenant(tenant_type="ИП", display_name="Иванов И.И.", phone="+7900")
            period = BillingPeriod(
                period_type="month",
                month_label="2026-06",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 30),
            )
            db.add_all([obj, tenant, period])
            db.commit()
            object_id = obj.id
            tenant_id = tenant.id
            period_id = period.id

        placement_response = self.client.post(
            "/placements",
            data={
                "object_id": object_id,
                "tenant_id": tenant_id,
                "rental_address": "Москва, Тверская, 1",
                "occupied_area": "75",
                "start_date": "2026-06-01",
                "is_active": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(placement_response.status_code, 303)

        for utility in ("heat", "electricity", "water", "cleaning"):
            response = self.client.post(
                "/charges",
                data={
                    "object_id": object_id,
                    "billing_period_id": period_id,
                    "utility_type": utility,
                    "input_mode": "amount",
                    "allocation_mode": "area",
                    "amount": "1000",
                },
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)

    def test_placement_validation_renders_html_error(self):
        with self.Session() as db:
            obj = PropertyObject(name="Р‘Р¦", address="РњРѕСЃРєРІР°", total_area=Decimal("150"))
            tenant = Tenant(tenant_type="РРџ", display_name="РРІР°РЅРѕРІ Р.Р.", phone="+7900")
            db.add_all([obj, tenant])
            db.commit()
            object_id = obj.id
            tenant_id = tenant.id

        response = self.client.post(
            "/placements",
            data={
                "object_id": object_id,
                "tenant_id": tenant_id,
                "rental_address": "РњРѕСЃРєРІР°, РўРІРµСЂСЃРєР°СЏ, 1",
                "occupied_area": "999",
                "start_date": "2026-06-01",
                "is_active": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("не может быть больше", response.text)
        self.assertIn("Новое размещение", response.text)

    def test_rejects_invalid_charge_links(self):
        response = self.client.post(
            "/charges",
            data={
                "object_id": 999,
                "billing_period_id": 999,
                "utility_type": "heat",
                "input_mode": "amount",
                "allocation_mode": "area",
                "amount": "500",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

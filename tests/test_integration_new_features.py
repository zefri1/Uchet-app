import unittest
import io
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Tenant, BillingPeriod, TenantPayment, PropertyObject, TrashBin

class IntegrationNewFeaturesTests(unittest.TestCase):
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

    def test_tenant_creation_with_initial_balance(self):
        response = self.client.post(
            "/tenants",
            data={
                "tenant_type": "ИП",
                "display_name": "Тестовый Арендатор",
                "phone": "123",
                "initial_balance": "1500.50",
                "note": "тест"
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            tenant = db.query(Tenant).filter_by(display_name="Тестовый Арендатор").first()
            self.assertIsNotNone(tenant)
            self.assertEqual(tenant.initial_balance, Decimal("1500.50"))
            
    def test_payments_endpoints(self):
        # Setup period and tenant
        with self.Session() as db:
            p = BillingPeriod(
                period_type="month",
                month_label="2026-06",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 30)
            )
            t = Tenant(
                tenant_type="ООО",
                display_name="Ромашка",
                phone="123",
                initial_balance=Decimal("0.00")
            )
            db.add_all([p, t])
            db.commit()
            period_id = p.id
            tenant_id = t.id

        # 1. Create payment
        response = self.client.post(
            "/payments",
            data={
                "tenant_id": tenant_id,
                "billing_period_id": period_id,
                "amount": "5000.00",
                "payment_date": "2026-06-10",
                "comment": "Платежка 44"
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            pay = db.query(TenantPayment).first()
            self.assertIsNotNone(pay)
            self.assertEqual(pay.amount, Decimal("5000.00"))
            self.assertEqual(pay.comment, "Платежка 44")
            pay_id = pay.id

        # 2. Edit payment
        response = self.client.post(
            f"/payments/{pay_id}/edit",
            data={
                "tenant_id": tenant_id,
                "billing_period_id": period_id,
                "amount": "6000.00",
                "payment_date": "2026-06-11",
                "comment": "Платежка 44 ред"
            },
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            pay = db.get(TenantPayment, pay_id)
            self.assertEqual(pay.amount, Decimal("6000.00"))
            self.assertEqual(pay.comment, "Платежка 44 ред")

        # 3. Delete payment (moves to trash)
        response = self.client.post(
            f"/payments/{pay_id}/delete",
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            pay = db.get(TenantPayment, pay_id)
            self.assertIsNone(pay)  # Deleted from main table
            
            trash = db.query(TrashBin).filter_by(entity_type="tenant_payment").first()
            self.assertIsNotNone(trash)
            trash_id = trash.id

        # 4. Restore payment from trash
        response = self.client.post(
            f"/trash/{trash_id}/restore",
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        
        with self.Session() as db:
            pay = db.get(TenantPayment, pay_id)
            self.assertIsNotNone(pay)  # Successfully restored!
            self.assertEqual(pay.amount, Decimal("6000.00"))
            self.assertEqual(pay.comment, "Платежка 44 ред")

    def test_settings_and_templates(self):
        resp = self.client.get("/settings/templates/objects")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        resp = self.client.get("/settings/templates/tenants")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        resp = self.client.get("/settings")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Резервное копирование", resp.text)

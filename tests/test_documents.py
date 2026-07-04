from __future__ import annotations

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import BillingPeriod, ChargeAllocation, PropertyObject, Tenant, UtilityCharge
from app.services import documents


class DocumentGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_generated_dir = documents.GENERATED_DIR
        documents.GENERATED_DIR = Path(self.tmpdir.name)
        documents.GENERATED_DIR.mkdir(parents=True, exist_ok=True)

        self.obj = PropertyObject(name="БЦ Север", address="Москва", total_area=Decimal("100"))
        self.tenant = Tenant(tenant_type="ООО", display_name="Альфа/Сервис")
        self.period = BillingPeriod(
            period_type="month",
            month_label="2026/06:итог",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
        )
        self.charge = UtilityCharge(
            object=self.obj,
            billing_period=self.period,
            utility_type="heat",
            input_mode="amount",
            allocation_mode="area",
            amount=Decimal("1000"),
        )
        self.allocation = ChargeAllocation(
            billing_period=self.period,
            utility_charge=self.charge,
            object=self.obj,
            tenant=self.tenant,
            base_area=Decimal("100"),
            share_value=Decimal("1"),
            amount=Decimal("1000"),
            mode="area",
        )
        self.db.add_all([self.obj, self.tenant, self.period, self.charge, self.allocation])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        documents.GENERATED_DIR = self.original_generated_dir
        self.tmpdir.cleanup()

    def test_invoice_generation_uses_safe_unique_filename(self) -> None:
        first = documents.generate_invoice_docx(self.db, self.period, self.tenant)
        second = documents.generate_invoice_docx(self.db, self.period, self.tenant)

        first_path = Path(first.file_path)
        second_path = Path(second.file_path)

        self.assertTrue(first_path.exists())
        self.assertTrue(second_path.exists())
        self.assertNotEqual(first.file_path, second.file_path)
        self.assertNotIn("/", first_path.name)
        self.assertNotIn(":", first_path.name)
        self.assertTrue(first_path.name.startswith("invoice_"))

    def test_register_generation_xlsx(self) -> None:
        reg = documents.generate_register_xlsx(self.db, self.period)
        reg_path = Path(reg.file_path)
        self.assertTrue(reg_path.exists())
        self.assertTrue(reg_path.name.startswith("register_"))
        self.assertEqual(reg.document_type, "register")

    def test_invoice_generation_xlsx(self) -> None:
        inv = documents.generate_invoice_xlsx(self.db, self.period, self.tenant)
        inv_path = Path(inv.file_path)
        self.assertTrue(inv_path.exists())
        self.assertTrue(inv_path.name.startswith("invoice_"))
        self.assertEqual(inv.document_type, "invoice_xlsx")

    def test_act_generation_xlsx(self) -> None:
        act = documents.generate_act_xlsx(self.db, self.period, self.tenant)
        act_path = Path(act.file_path)
        self.assertTrue(act_path.exists())
        self.assertTrue(act_path.name.startswith("act_"))
        self.assertEqual(act.document_type, "act_xlsx")


if __name__ == "__main__":
    unittest.main()

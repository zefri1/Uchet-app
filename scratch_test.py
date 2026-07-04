import sys
import os
from sqlalchemy import select
from app.db import SessionLocal
from app.models import BillingPeriod, Tenant
from app.services import documents

def test_generation():
    db = SessionLocal()
    try:
        # Get the latest period
        period = db.scalars(select(BillingPeriod).order_by(BillingPeriod.start_date.desc())).first()
        if not period:
            print("No billing periods found.")
            return
        
        print(f"Testing with period: {period.id} ({period.month_label or period.start_date})")
        
        # Try generating register for the period
        print("Generating register...")
        try:
            reg = documents.generate_register_xlsx(db, period)
            print("Register generated:", reg.file_path)
        except Exception as e:
            print("Failed register generation:", e)
            import traceback
            traceback.print_exc()

        # Get a tenant
        tenant = db.scalars(select(Tenant)).first()
        if tenant:
            print(f"Testing with tenant: {tenant.id} ({tenant.display_name})")
            print("Generating invoice xlsx...")
            try:
                inv_x = documents.generate_invoice_xlsx(db, period, tenant)
                print("Invoice XLSX generated:", inv_x.file_path)
            except Exception as e:
                print("Failed invoice XLSX generation:", e)
                import traceback
                traceback.print_exc()

            print("Generating act xlsx...")
            try:
                act_x = documents.generate_act_xlsx(db, period, tenant)
                print("Act XLSX generated:", act_x.file_path)
            except Exception as e:
                print("Failed act XLSX generation:", e)
                import traceback
                traceback.print_exc()
        else:
            print("No tenants found.")
    finally:
        db.close()

if __name__ == "__main__":
    test_generation()

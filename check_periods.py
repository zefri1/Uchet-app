from sqlalchemy import select
from app.db import SessionLocal
from app.models import BillingPeriod, ChargeAllocation, Tenant

def check_periods():
    db = SessionLocal()
    try:
        periods = db.scalars(select(BillingPeriod).order_by(BillingPeriod.start_date.desc())).all()
        print(f"Total periods: {len(periods)}")
        for p in periods:
            allocs = db.scalars(select(ChargeAllocation).where(ChargeAllocation.billing_period_id == p.id)).all()
            print(f"Period ID: {p.id}, Month: {p.month_label or p.start_date}, Allocations count: {len(allocs)}")
            for a in allocs[:3]:
                print(f"  Alloc - Tenant ID: {a.tenant_id}, Object ID: {a.object_id}, Amount: {a.amount}")
    finally:
        db.close()

if __name__ == "__main__":
    check_periods()

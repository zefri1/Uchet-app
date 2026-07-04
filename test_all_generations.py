from sqlalchemy import select
from app.db import SessionLocal
from app.models import BillingPeriod, Tenant
from app.services import documents
import traceback

def run_all_generations():
    db = SessionLocal()
    try:
        periods = db.scalars(select(BillingPeriod)).all()
        tenants = db.scalars(select(Tenant)).all()
        print(f"Periods: {len(periods)}, Tenants: {len(tenants)}")
        for p in periods:
            print(f"\n--- Period {p.id} ({p.month_label or p.start_date}) ---")
            
            # Scope: All (Register)
            try:
                reg = documents.generate_register_xlsx(db, p)
                print(f"Register generated successfully: {reg.file_path}")
            except Exception as e:
                print(f"Register generation failed: {type(e).__name__}: {e}")
                
            # Scope: Single Tenant
            for t in tenants:
                print(f"  Tenant {t.id} ({t.display_name})")
                try:
                    inv_docx = documents.generate_invoice_docx(db, p, t)
                    print(f"    Invoice DOCX: {inv_docx.file_path}")
                except Exception as e:
                    print(f"    Invoice DOCX failed: {type(e).__name__}: {e}")
                    
                try:
                    act_docx = documents.generate_act_docx(db, p, t)
                    print(f"    Act DOCX: {act_docx.file_path}")
                except Exception as e:
                    print(f"    Act DOCX failed: {type(e).__name__}: {e}")

                try:
                    inv_xlsx = documents.generate_invoice_xlsx(db, p, t)
                    print(f"    Invoice XLSX: {inv_xlsx.file_path}")
                except Exception as e:
                    print(f"    Invoice XLSX failed: {type(e).__name__}: {e}")

                try:
                    act_xlsx = documents.generate_act_xlsx(db, p, t)
                    print(f"    Act XLSX: {act_xlsx.file_path}")
                except Exception as e:
                    print(f"    Act XLSX failed: {type(e).__name__}: {e}")
                    
                try:
                    reg_xlsx = documents.generate_register_xlsx(db, p, t)
                    print(f"    Register XLSX: {reg_xlsx.file_path}")
                except Exception as e:
                    print(f"    Register XLSX failed: {type(e).__name__}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_all_generations()

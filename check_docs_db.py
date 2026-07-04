from sqlalchemy import select
from app.db import SessionLocal
from app.main import get_grouped_documents

def check_grouping():
    db = SessionLocal()
    try:
        grouped = get_grouped_documents(db)
        print(f"Grouped periods count: {len(grouped)}")
        for idx, item in enumerate(grouped):
            period = item["period"]
            print(f"Period {idx}: {period.id} ({period.month_label})")
            print(f"  Registers count: {len(item['registers'])}")
            print(f"  Tenants count: {len(item['tenants'])}")
            for t_data in item["tenants"]:
                print(f"    Tenant: {t_data['tenant_name']}")
                print(f"      Register: {t_data['register']}")
                print(f"      Invoice DOCX: {t_data['invoice_docx']}")
                print(f"      Invoice XLSX: {t_data['invoice_xlsx']}")
                print(f"      Act DOCX: {t_data['act_docx']}")
                print(f"      Act XLSX: {t_data['act_xlsx']}")
    finally:
        db.close()

if __name__ == "__main__":
    check_grouping()

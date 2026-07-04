import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("Testing POST /objects...")
try:
    response = client.post("/objects", data={"name": "Test Object", "address": "Test Address", "total_area": "100.00", "note": ""}, headers={"referer": "http://testserver/v2/directory?tab=objects"})
    print(f"Status Code: {response.status_code}")
    print(f"Location: {response.headers.get('Location')}")
    if response.status_code >= 400:
        print("Error response:")
        print(response.text[:2000])
except Exception as e:
    print("Exception occurred:")
    import traceback
    traceback.print_exc()

print("\nTesting POST /tenants...")
try:
    response = client.post("/tenants", data={"tenant_type": "ИП", "display_name": "Test Tenant", "phone": "", "initial_balance": "0.00", "note": ""}, headers={"referer": "http://testserver/v2/directory?tab=tenants"})
    print(f"Status Code: {response.status_code}")
    print(f"Location: {response.headers.get('Location')}")
    if response.status_code >= 400:
        print("Error response:")
        print(response.text[:2000])
except Exception as e:
    print("Exception occurred:")
    import traceback
    traceback.print_exc()

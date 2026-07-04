import urllib.request
import urllib.parse

def test_request():
    try:
        # Test post to generate for single tenant
        data = urllib.parse.urlencode({
            "billing_period_id": 1,
            "tenant_id": "1",
            "scope": "single"
        }).encode("utf-8")
        
        req = urllib.request.Request("http://127.0.0.1:8002/documents/generate", data=data, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                print("POST /documents/generate (single) status:", response.status)
        except urllib.error.HTTPError as e:
            print("POST /documents/generate (single) HTTPError status:", e.code)
            print("Response:", e.read().decode("utf-8", errors="ignore")[:1000])
    except Exception as e:
        print("Request failed:", e)

if __name__ == "__main__":
    test_request()

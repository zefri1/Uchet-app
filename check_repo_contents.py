import urllib.request
import json
import base64

def get_contents(repo, path=""):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {repo}/{path}: {e}")
        return None

for repo in ["codexstar69/bug-hunter", "fugazi/test-automation-skills-agents"]:
    print(f"\n--- {repo} ---")
    data = get_contents(repo)
    if data:
        if isinstance(data, list):
            for item in data:
                print(item['name'], item['type'])
        else:
            print(data)

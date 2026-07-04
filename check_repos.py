import urllib.request
import json

repos = [
    "openai/skills",
    "addyosmani/agent-skills",
    "fugazi/test-automation-skills-agents",
    "automata-network/agent-skills",
    "codexstar69/bug-hunter",
    "anthropics/claude-code",
    "Dimillian/Skills",
    "openclaw/skills",
    "clear-solutions/unit-tests-skills",
    "eigent-ai/agent-skills"
]

for repo in repos:
    url = f"https://api.github.com/repos/{repo}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"[OK] {repo} - {data.get('description', '')}")
    except Exception as e:
        print(f"[FAIL] {repo} - {e}")

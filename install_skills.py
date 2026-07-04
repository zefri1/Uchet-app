import urllib.request
import json
import base64
import os
import re

SKILLS_TO_INSTALL = [
    {"repo": "codexstar69/bug-hunter", "path": "skills/hunter", "name": "bug-hunter"},
    {"repo": "fugazi/test-automation-skills-agents", "path": "skills/qa-test-planner", "name": "qa-test-planner"},
    {"repo": "fugazi/test-automation-skills-agents", "path": "skills/api-testing", "name": "api-testing"},
    {"repo": "fugazi/test-automation-skills-agents", "path": "skills/playwright-regression-testing", "name": "playwright-regression-testing"},
    {"repo": "addyosmani/agent-skills", "path": "skills/code-review-and-quality", "name": "code-review"}
]

def get_contents(repo, path=""):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {repo}/{path}: {e}")
        return None

def download_skill(repo, path, skill_name):
    data = get_contents(repo, path)
    if not data: return
    
    skill_dir = f".antigravity/skills/{skill_name}"
    os.makedirs(skill_dir, exist_ok=True)
    
    if isinstance(data, dict) and data.get("type") == "file":
        content = base64.b64decode(data['content']).decode('utf-8')
        
        if not content.startswith("---"):
            content = f"---\nname: {skill_name}\ndescription: Auto-imported from {repo}\n---\n\n" + content
            
        with open(f"{skill_dir}/SKILL.md", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Installed {skill_name} from {repo}")
    elif isinstance(data, list):
        for item in data:
            if item['name'] == 'SKILL.md' or item['name'].endswith('.md'):
                sub_data = get_contents(repo, item['path'])
                if sub_data and sub_data.get("type") == "file":
                    content = base64.b64decode(sub_data['content']).decode('utf-8')
                    if not content.startswith("---"):
                        content = f"---\nname: {skill_name}\ndescription: Skill imported from {repo}\n---\n\n" + content
                    with open(f"{skill_dir}/SKILL.md", "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Installed {skill_name} from {repo}")
                    return

for skill in SKILLS_TO_INSTALL:
    download_skill(skill["repo"], skill["path"], skill["name"])

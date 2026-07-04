import urllib.request
import json
import base64
import os
import re

def get_contents(repo, path=""):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {repo}/{path}: {e}")
        return None

def download_skill(repo, path, skill_name, agent_format="antigravity"):
    data = get_contents(repo, path)
    if not data: return
    
    skill_dir = f".antigravity/skills/{skill_name}"
    os.makedirs(skill_dir, exist_ok=True)
    
    if isinstance(data, dict) and data.get("type") == "file":
        content = base64.b64decode(data['content']).decode('utf-8')
        
        # Ensure it has frontmatter
        if not content.startswith("---"):
            content = f"---\nname: {skill_name}\ndescription: Auto-imported from {repo}\n---\n\n" + content
            
        with open(f"{skill_dir}/SKILL.md", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Installed {skill_name} from {repo}")
    elif isinstance(data, list):
        # Look for SKILL.md or something similar
        for item in data:
            if item['name'] == 'SKILL.md':
                download_skill(repo, item['path'], skill_name)
                return

# Let's see what skills are in these repos
for repo in ["codexstar69/bug-hunter", "fugazi/test-automation-skills-agents", "addyosmani/agent-skills", "eigent-ai/agent-skills"]:
    print(f"\n--- {repo} ---")
    data = get_contents(repo, "skills")
    if data and isinstance(data, list):
        for item in data:
            print(item['name'], item['type'])

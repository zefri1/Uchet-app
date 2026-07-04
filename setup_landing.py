import os

# 1. Update main.py
with open('app/main.py', encoding='utf-8') as f:
    content = f.read()

content = content.replace('@app.get("/")\ndef dashboard_page(', '@app.get("/dashboard")\ndef dashboard_page(')

if '@app.get("/")\ndef landing_page(' not in content:
    content += """

@app.get("/")
def landing_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "landing.html", db)
"""
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update base.html nav link
with open('app/templates/base.html', encoding='utf-8') as f:
    base_html = f.read()
    
base_html = base_html.replace('href="/"', 'href="/dashboard"')
with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base_html)


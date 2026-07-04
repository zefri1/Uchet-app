import os

with open('app/templates/v2/base_v2.html', encoding='utf-8') as f:
    content = f.read()

# Replace any href="/" with href="/dashboard" 
content = content.replace('href="/"', 'href="/dashboard"')

with open('app/templates/v2/base_v2.html', 'w', encoding='utf-8') as f:
    f.write(content)


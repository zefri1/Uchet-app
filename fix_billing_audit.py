import re

with open('app/templates/v2/billing.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the button containing showAudit(this)
# Example: <button class="btn btn-secondary btn-compact" style="font-size:11px;" data-audit='{{ item.audit_payload }}' onclick="showAudit(this)">Формула</button>
# Let's replace the whole tag. We match <button ... onclick="showAudit(this)" ...>Формула</button>
pattern = r"<button([^>]*)onclick=\"showAudit\(this\)\"([^>]*)>(.*?)</button>"

def repl(match):
    attrs1 = match.group(1)
    attrs2 = match.group(2)
    body = match.group(3)
    
    # Merge attributes and remove style
    all_attrs = attrs1 + " " + attrs2
    all_attrs = re.sub(r'style="[^"]*"', '', all_attrs) # remove style="font-size:11px;"
    all_attrs = re.sub(r'\s+', ' ', all_attrs).strip()
    
    svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    
    return f'<button {all_attrs} onclick="showAudit(this)">{svg} {body}</button>'

content = re.sub(pattern, repl, content)

# Check if double classes occurred
content = content.replace('class="btn btn-secondary btn-compact" class="btn btn-secondary btn-compact"', 'class="btn btn-secondary btn-compact"')

with open('app/templates/v2/billing.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Billing audit button updated.")

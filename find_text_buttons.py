import os
import re

button_pattern = re.compile(r'<button([^>]*)>(.*?)</button>', re.DOTALL)
a_btn_pattern = re.compile(r'<a\s+[^>]*class="[^"]*btn[^"]*"[^>]*>(.*?)</a>', re.DOTALL)

out = []

def analyze_html(filepath, filename):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Analyze buttons
    for attrs, body in button_pattern.findall(content):
        clean_body = body.strip()
        if clean_body and '<svg' not in clean_body and any(c.isalpha() for c in clean_body):
            out.append(f"{filename} | BUTTON: {attrs.strip()} | Content: {clean_body}")
            
    # Analyze a.btn
    for body in a_btn_pattern.findall(content):
        clean_body = body.strip()
        if clean_body and '<svg' not in clean_body and any(c.isalpha() for c in clean_body):
            out.append(f"{filename} | A_BTN | Content: {clean_body}")

for root, dirs, files in os.walk('app/templates/v2'):
    for file in files:
        if file.endswith('.html'):
            analyze_html(os.path.join(root, file), file)

with open('scratch/text_buttons.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Done. Results in scratch/text_buttons.txt")

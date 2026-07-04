import os
import re

button_pattern = re.compile(r'<button([^>]*)>(.*?)</button>', re.DOTALL)

out = []
for root, dirs, files in os.walk('app/templates/v2'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            matches = button_pattern.findall(content)
            for attrs, body in matches:
                # check if there's no tag but some non-ascii chars or empty body
                clean_body = body.strip()
                if '<svg' not in clean_body and clean_body:
                    # check if body has emojis or unicode characters
                    unicode_chars = [f"\\u{ord(c):04x} ({c})" for c in clean_body]
                    out.append(f"{file} button attributes: {attrs.strip()} | Content: {' '.join(unicode_chars)}")

with open('scratch/button_contents.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Button analysis done.")

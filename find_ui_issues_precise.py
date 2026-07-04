import os
import re

# Correct emoji patterns:
# 1. 32-bit emojis: \U00010000 to \U0010FFFF
# 2. 16-bit miscellaneous symbols and dingbats: \u2600 to \u27BF
emoji_pattern = re.compile(r'[\U00010000-\U0010FFFF]|[\u2600-\u27BF]', flags=re.UNICODE)

out = []
for root, dirs, files in os.walk('app/templates/v2'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for idx, line in enumerate(lines):
                # check emojis
                found_emojis = emoji_pattern.findall(line)
                # Filter out standard punctuation or letters in case they slip in (though \u2600-\u27BF is safe)
                if found_emojis:
                    # Let's verify each found character is actually an emoji/symbol
                    real_emojis = [e for e in found_emojis if ord(e) > 127]
                    if real_emojis:
                        out.append(f"EMOJI in {file}:{idx+1}: {''.join(real_emojis)} -> {line.strip()}")
                
                # Check for "всех арендаторов" or "сформировать"
                if 'сформировать' in line.lower() or 'всех арендаторов' in line.lower():
                    out.append(f"TERM in {file}:{idx+1} -> {line.strip()}")

# Let's also check static files/style.css hover states
with open('app/static/style.css', 'r', encoding='utf-8') as f:
    style_lines = f.readlines()
for idx, line in enumerate(style_lines):
    if ':hover' in line and ('background' in line or 'color' in line or 'border' in line):
        out.append(f"HOVER in style.css:{idx+1} -> {line.strip()}")
        # capture context
        start = max(0, idx - 2)
        end = min(len(style_lines), idx + 3)
        context = "".join(style_lines[start:end])
        out.append(f"CONTEXT:\n{context}---")

with open('scratch/real_search_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Done. Results in scratch/real_search_results.txt")

import os
import re

search_terms = ['сформировать', 'всех', 'тариф', 'удалить', 'btn', 'hover', 'оранже']

emoji_pattern = re.compile(r'[\u2600-\u27BF]|[\u1F300-\u1F9FF]|[\u1F600-\u1F64F]|[\u1F680-\u1F6FF]')

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
                if found_emojis:
                    out.append(f"EMOJI in {file}:{idx+1}: {found_emojis} -> {line.strip()}")
                # check terms
                for term in ['сформировать', 'всех арендаторов', 'удалить']:
                    if term in line.lower():
                        out.append(f"TERM '{term}' in {file}:{idx+1}: {line.strip()}")

# Write to file to prevent cp1251 console encoding errors
os.makedirs('scratch', exist_ok=True)
with open('scratch/search_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Search done. Results in scratch/search_results.txt")

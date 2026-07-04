import os

search_terms = ['рассчитан', 'расчитан', 'статус', 'период', 'тариф', 'желтый', 'yellow', 'warning']
out = []

for root, dirs, files in os.walk('app/templates/v2'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            for idx, line in enumerate(lines):
                # Search for terms
                for term in search_terms:
                    if term in line.lower():
                        out.append(f"{file}:{idx+1} ({term}) -> {line.strip()}")
                        break

with open('scratch/status_search.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Search done.")

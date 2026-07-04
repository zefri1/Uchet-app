import sys

with open('app/main.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'RedirectResponse(url="/")' in line:
        print("Redirect to / found at line", i)
    if 'RedirectResponse(url="/?' in line:
        print("Redirect to /? found at line", i)


with open('app/static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find all CSS blocks with :hover
import re
hover_blocks = re.findall(r'([^{}]*:[^{}]*hover[^{}]*\{[^{}]*\})', content, re.DOTALL)

with open('scratch/hover_blocks.txt', 'w', encoding='utf-8') as f:
    for block in hover_blocks:
        f.write(block.strip() + "\n\n")
print(f"Found {len(hover_blocks)} hover blocks. Saved in scratch/hover_blocks.txt")

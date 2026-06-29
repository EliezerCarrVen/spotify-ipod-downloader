import sys

with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(81, 581): # 82 to 581 in 1-indexed
    if i < len(lines):
        line = lines[i]
        if line.strip():
            lines[i] = "    " + line
        else:
            lines[i] = line # keep empty lines empty

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

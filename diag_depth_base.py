import re

with open('base.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

depth = 0
for i, line in enumerate(lines, 1):
    starts = len(re.findall(r'<div\b', line))
    ends = len(re.findall(r'</div\b', line))
    if starts > 0 or ends > 0:
        depth += starts - ends
        print(f"L{i:3}: depth={depth:2} | +{starts} -{ends} | {line.strip()[:60]}")

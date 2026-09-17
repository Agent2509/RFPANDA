with open('backend/app/routers/query.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'full_text = "' in line and 'join' not in line:
        continue
    if '".join(' in line and 'full_text' not in line:
        new_lines.append('        full_text = "\\n\\n".join(\n')
        continue
    if 'f"--- Page {p.page_number} ---' in line and '{p.text}' not in line:
        continue
    if '{p.text}" for p in payload.pages' in line and '--- Page' not in line:
        new_lines.append('            f"--- Page {p.page_number} ---\\n{p.text}" for p in payload.pages if p.text.strip()\n')
        continue
    new_lines.append(line)

with open('backend/app/routers/query.py', 'w') as f:
    f.writelines(new_lines)

import re

with open('frontend/src/lib/pdf-fallback.ts', 'r') as f:
    content = f.read()

# Replace /api/query/documents/fallback-parse with /api/documents/fallback-parse
content = content.replace("/api/query/documents/fallback-parse", "/api/documents/fallback-parse")

with open('frontend/src/lib/pdf-fallback.ts', 'w') as f:
    f.write(content)

print("Done")

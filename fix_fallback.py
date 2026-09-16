import re

with open('frontend/src/lib/pdf-fallback.ts', 'r') as f:
    content = f.read()

# Replace edgeFunctionEndpoint assignment
new_code = """
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://rfpanda-backend.onrender.com';
  const endpoint = `${backendUrl.replace(/\\/$/, '')}/api/query/documents/fallback-parse`;
"""

content = re.sub(
    r"const edgeFunctionEndpoint = .*?;",
    new_code.strip(),
    content,
    flags=re.DOTALL
)

content = content.replace("fetch(edgeFunctionEndpoint", "fetch(endpoint")

with open('frontend/src/lib/pdf-fallback.ts', 'w') as f:
    f.write(content)

print("Done")

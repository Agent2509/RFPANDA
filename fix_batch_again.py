with open('backend/app/routers/query.py', 'r') as f:
    content = f.read()

content = content.replace("batch_size=8", "batch_size=4")

with open('backend/app/routers/query.py', 'w') as f:
    f.write(content)

print("Batch size fixed to 4")

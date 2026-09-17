with open('backend/app/routers/query.py', 'r') as f:
    content = f.read()

content = content.replace("batch_size=15", "batch_size=8")
content = content.replace("delay_between_batches=62.0", "delay_between_batches=65.0")

with open('backend/app/routers/query.py', 'w') as f:
    f.write(content)

print("Batch size fixed")

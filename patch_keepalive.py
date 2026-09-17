import re

with open('backend/app/routers/query.py', 'r') as f:
    content = f.read()

keep_alive_code = """
        # Keep-alive loop to prevent Render from spinning down the free instance
        import httpx
        async def ping_self():
            try:
                # Render provides the external URL in the RENDER_EXTERNAL_URL env var
                import os
                url = os.getenv("RENDER_EXTERNAL_URL", "http://127.0.0.0:8000")
                async with httpx.AsyncClient() as client:
                    await client.get(f"{url}/api/health")
            except:
                pass
        
        # Ping immediately to ensure httpx is working
        await ping_self()
        
        chunk_texts = [c.content for c in chunk_results]
        
        # Embed with manual loop so we can ping ourselves every batch to keep Render alive!
        all_embeddings = []
        for i in range(0, len(chunk_texts), 4):
            batch = chunk_texts[i:i + 4]
            batch_vectors = await embedding_svc.create_embeddings(batch, input_type="document", model=None)
            all_embeddings.extend(batch_vectors)
            
            if i + 4 < len(chunk_texts):
                await ping_self()
                await asyncio.sleep(65.0)
                
        embeddings = all_embeddings
"""

# Replace the embed_documents call with the manual loop + keep-alive
pattern = r'chunk_texts = \[c\.content for c in chunk_results\].*?delay_between_batches=65\.0\n\s*\)'

content = re.sub(pattern, keep_alive_code.strip(), content, flags=re.DOTALL)

with open('backend/app/routers/query.py', 'w') as f:
    f.write(content)

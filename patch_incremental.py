import re

with open('backend/app/routers/query.py', 'r') as f:
    content = f.read()

incremental_code = """
        # Embed with manual loop so we can ping ourselves every batch to keep Render alive!
        for i in range(0, len(chunk_texts), 4):
            batch = chunk_texts[i:i + 4]
            batch_vectors = await embedding_svc.create_embeddings(batch, input_type="document", model=None)
            
            # Incremental DB Insert so the UI updates live!
            chunk_rows = [
                {
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": chunk_results[i + idx].chunk_index,
                    "content": chunk_results[i + idx].content,
                    "embedding": batch_vectors[idx],
                    "token_count": chunk_results[i + idx].token_count,
                    "metadata": {
                        **chunk_results[i + idx].metadata,
                        "parser": parser_used or "pdfjs_client_fallback",
                    },
                }
                for idx in range(len(batch_vectors))
            ]
            # Don't delete on incremental inserts, just insert
            if i == 0:
                await vector_svc.delete_and_insert_chunks(document_id=document_id, chunks=chunk_rows)
            else:
                # Assuming delete_and_insert_chunks can just do an insert if we bypass delete
                # Actually, let's just use the Supabase client directly to append
                await vector_svc.client.table("document_chunks").insert(chunk_rows).execute()
                
            # Keep-alive ping and throttle
            if i + 4 < len(chunk_texts):
                await ping_self()
                await asyncio.sleep(65.0)
                
        # Final status update
        import datetime
        await vector_svc._execute_write(
            "UPDATE documents SET status = $1, error_message = NULL, updated_at = $2, processed_at = $2 WHERE id = $3",
            "processed", datetime.datetime.utcnow().isoformat(), document_id
        )
        return
"""

# We need to replace the old loop AND the old insert logic.
# The old insert logic is:
#         embeddings = all_embeddings
#
#         if len(embeddings) != len(chunk_results):
# ...
#         await vector_svc.delete_and_insert_chunks(document_id=document_id, chunks=chunk_rows)
#
#         import datetime

# Let's find the start of the old loop:
pattern = r'all_embeddings = \[\]\n\s*for i in range\(0, len\(chunk_texts\), 4\):.*?await vector_svc\.delete_and_insert_chunks\(document_id=document_id, chunks=chunk_rows\)'

content = re.sub(pattern, incremental_code.strip(), content, flags=re.DOTALL)

with open('backend/app/routers/query.py', 'w') as f:
    f.write(content)

import re

with open('backend/app/routers/query.py', 'r') as f:
    content = f.read()

# Replace the broken vector_svc.client code
old_code = """
            # Don't delete on incremental inserts, just insert
            if i == 0:
                await vector_svc.delete_and_insert_chunks(document_id=document_id, user_id=user_id, chunks=chunk_rows)
            else:
                # Assuming delete_and_insert_chunks can just do an insert if we bypass delete
                # Actually, let's just use the Supabase client directly to append
                await vector_svc.client.table("document_chunks").insert(chunk_rows).execute()
"""

new_code = """
            # Incremental insert directly via HTTP
            client = await vector_svc._get_client()
            insert_url = f"{vector_svc.supabase_url}/rest/v1/document_chunks"
            resp = await client.post(insert_url, json=chunk_rows, headers=vector_svc._get_headers())
            if resp.status_code not in (200, 201):
                import logging
                logging.getLogger("apextender.query").error(f"Incremental chunk insert failed: {resp.text}")
"""

content = content.replace(old_code.strip(), new_code.strip())

# Also fix the final status update which used _execute_write (which doesn't exist!)
old_status = """
        # Final status update
        import datetime
        await vector_svc._execute_write(
            "UPDATE documents SET status = $1, error_message = NULL, updated_at = $2, processed_at = $2 WHERE id = $3",
            "processed", datetime.datetime.utcnow().isoformat(), document_id
        )
"""

new_status = """
        # Final status update
        await vector_svc.update_document_status(document_id, "processed")
"""

content = content.replace(old_status.strip(), new_status.strip())

with open('backend/app/routers/query.py', 'w') as f:
    f.write(content)


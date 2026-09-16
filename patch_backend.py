import re

# 1. Update embedding.py
with open('backend/app/services/embedding.py', 'r') as f:
    emb_content = f.read()

emb_content = emb_content.replace(
    'async def embed_documents(\n        self,\n        texts: List[str],\n        batch_size: int = 64,\n        model: Optional[str] = None\n    ) -> List[List[float]]:',
    'async def embed_documents(\n        self,\n        texts: List[str],\n        batch_size: int = 64,\n        model: Optional[str] = None,\n        delay_between_batches: float = 0.0\n    ) -> List[List[float]]:'
)

if "await asyncio.sleep(delay_between_batches)" not in emb_content:
    emb_content = emb_content.replace(
        'all_embeddings.extend(batch_vectors)',
        'all_embeddings.extend(batch_vectors)\n            if delay_between_batches > 0 and i + batch_size < len(texts):\n                import asyncio\n                await asyncio.sleep(delay_between_batches)'
    )

with open('backend/app/services/embedding.py', 'w') as f:
    f.write(emb_content)


# 2. Update query.py
with open('backend/app/routers/query.py', 'r') as f:
    query_content = f.read()

bg_task_code = """
async def _process_fallback_ingestion_background(
    document_id: str,
    full_text: str,
    parser_used: str,
    user_id: str,
):
    try:
        from app.services.vector_store import get_vector_store
        from app.services.embedding import get_embedding_service
        from app.services.chunker import SemanticChunker
        import asyncio

        vector_svc = get_vector_store()
        embedding_svc = get_embedding_service()

        chunker = SemanticChunker(target_tokens=600, overlap_tokens=100, max_tokens=1000)
        chunk_results = chunker.chunk_text(full_text)

        if not chunk_results:
            await vector_svc.update_document_status(
                document_id, "failed",
                error_message="Fallback parser produced no valid text chunks."
            )
            return

        chunk_texts = [c.content for c in chunk_results]
        
        # Free Tier Throttling: 10k TPM limit means we can only do ~15 chunks (9k tokens) per minute
        # We will batch 15 chunks and wait 62 seconds between batches.
        embeddings = await embedding_svc.embed_documents(
            chunk_texts, 
            batch_size=15, 
            delay_between_batches=62.0
        )

        if len(embeddings) != len(chunk_results):
            await vector_svc.update_document_status(
                document_id, "failed",
                error_message=f"Embedding mismatch: expected {len(chunk_results)}, got {len(embeddings)}"
            )
            return

        chunk_rows = [
            {
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": cr.chunk_index,
                "content": cr.content,
                "embedding": embeddings[idx],
                "token_count": cr.token_count,
                "metadata": {
                    **cr.metadata,
                    "parser": parser_used or "pdfjs_client_fallback",
                },
            }
            for idx, cr in enumerate(chunk_results)
        ]

        await vector_svc.delete_and_insert_chunks(document_id=document_id, chunks=chunk_rows)

        import datetime
        await vector_svc._execute_write(
            "UPDATE documents SET status = $1, error_message = NULL, updated_at = $2, processed_at = $2 WHERE id = $3",
            "processed", datetime.datetime.utcnow().isoformat(), document_id
        )

    except Exception as e:
        import logging
        logging.getLogger("apextender.query").error(f"Background ingestion failed: {e}", exc_info=True)
        from app.services.vector_store import get_vector_store
        vector_svc = get_vector_store()
        await vector_svc.update_document_status(
            document_id, "failed",
            error_message=f"Background ingestion error: {str(e)}"
        )


@router.post("/documents/fallback-parse")
@limiter.limit("5/minute")
async def fallback_parse_ingest(
    request: Request,
    payload: FallbackParseRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    vector_svc: SupabaseVectorStore = Depends(get_vector_store)
):
    if not payload.extracted_text and not payload.pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extracted text or pages provided in fallback payload."
        )

    doc = await vector_svc.get_document(payload.document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or unauthorized."
        )

    await vector_svc.update_document_status(payload.document_id, "fallback_processing")

    if payload.pages:
        full_text = "\\n\\n".join(
            f"--- Page {p.page_number} ---\\n{p.text}" for p in payload.pages if p.text.strip()
        )
    else:
        full_text = payload.extracted_text or ""

    if not full_text.strip():
        await vector_svc.update_document_status(
            payload.document_id, "failed",
            error_message="Fallback text was empty after assembly."
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fallback text was empty after assembly."
        )

    background_tasks.add_task(
        _process_fallback_ingestion_background,
        document_id=payload.document_id,
        full_text=full_text,
        parser_used=payload.parser_used or "pdfjs_client_fallback",
        user_id=user.id
    )

    return {"status": "processing_in_background", "message": "Fallback ingestion queued for background processing."}
"""

# Replace the whole fallback_parse_ingest function
pattern = r'@router\.post\("/documents/fallback-parse"\).*?(?=@router\.delete|$)'
query_content = re.sub(pattern, bg_task_code + "\n\n", query_content, flags=re.DOTALL)

# Add BackgroundTasks if missing
if "BackgroundTasks" not in query_content:
    query_content = query_content.replace(
        "from fastapi import APIRouter, Depends, HTTPException, status, Request",
        "from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Request"
    )

with open('backend/app/routers/query.py', 'w') as f:
    f.write(query_content)

print("Backend patched successfully")

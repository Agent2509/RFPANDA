"""
ApexTender v2.0 - RAG Query & Real-Time SSE Streaming Router
Handles user RFP questions, executes Voyage AI embeddings, searches Supabase pgvector,
touches document retention timestamps, and streams Groq LLM responses via Server-Sent Events.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Request
from fastapi.responses import StreamingResponse, JSONResponse

from app.auth import get_current_user, AuthenticatedUser
from app.schemas.query import (
    QueryRequest,
    SourceCitation,
    SourcesMetadata,
    TokenDelta,
    DoneEvent,
    ErrorEvent,
    FallbackParseRequest,
)
from app.services.embedding import get_embedding_service, VoyageEmbeddingService
from app.services.vector_store import get_vector_store, SupabaseVectorStore
from app.services.llm import get_llm_service, GroqLLMService

logger = logging.getLogger("apextender.query")

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api", tags=["RAG Query & Documents"])


@router.post("/query")
@limiter.limit("15/minute")
async def query_rag_stream(
    request: Request,
    payload: QueryRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    embedding_svc: VoyageEmbeddingService = Depends(get_embedding_service),
    vector_svc: SupabaseVectorStore = Depends(get_vector_store),
    llm_svc: GroqLLMService = Depends(get_llm_service)
):
    """
    Primary RFP Query Endpoint.
    Streams Server-Sent Events (SSE) including matched citations and LLM response tokens.
    """
    user_id = user.id
    start_time = time.time()

    # Step 0: Check Usage Limits
    try:
        await vector_svc.increment_query_count(user_id)
    except Exception as exc:
        if "Free tier limit reached" in str(exc):
            raise HTTPException(status_code=429, detail=str(exc))
        else:
            logger.error(f"Usage limit check failed: {str(exc)}")

    # Step 1: Query embedding via Voyage AI (1024d)
    try:
        query_embedding = await embedding_svc.embed_query(payload.query)
    except Exception as exc:
        logger.error(f"Failed to generate query embedding: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding service error: {str(exc)}"
        )

    # Step 2: pgvector similarity search via Supabase RPC match_documents
    try:
        matched_chunks = await vector_svc.match_documents(
            query_embedding=query_embedding,
            filter_user_id=user_id,
            filter_document_ids=payload.document_ids,
            match_threshold=payload.similarity_threshold,
            match_count=payload.match_count
        )
    except Exception as exc:
        logger.error(f"Vector search failed: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vector search error: {str(exc)}"
        )

    # Step 3: Refresh last_queried_at timestamp in background to reset 30-day retention
    if matched_chunks:
        unique_doc_ids = list(set(c["document_id"] for c in matched_chunks if c.get("document_id")))
        background_tasks.add_task(vector_svc.touch_document_last_queried, unique_doc_ids)

    # Step 4: SSE Async Generator
    async def sse_event_generator():
        # Case A: No context chunks found above threshold
        if not matched_chunks:
            error_payload = {
                "error": "Vector search returned no relevant chunks for the selected document(s). Try broadening your query or lowering the similarity threshold.",
                "code": "NO_CONTEXT_FOUND"
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
            return

        # Case B: Emit sources / metadata event
        sources_list = [
            {
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "file_name": c["file_name"],
                "page_number": c["page_number"],
                "section_header": c["section_header"],
                "similarity": c["similarity"],
                "snippet": c["content"][:240]
            }
            for c in matched_chunks
        ]
        sources_event_payload = json.dumps({"sources": sources_list})
        yield f"event: sources\ndata: {sources_event_payload}\n\n"
        # Mirror as metadata event for clients adhering to metadata event naming
        yield f"event: metadata\ndata: {sources_event_payload}\n\n"

        # Case C: Stream LLM token deltas
        token_count = 0
        try:
            async for token in llm_svc.stream_chat_completion(
                query=payload.query,
                context_chunks=matched_chunks,
                model=payload.model
            ):
                token_count += 1
                token_payload = json.dumps({"delta": token, "text": token})
                yield f"event: token\ndata: {token_payload}\n\n"

            # Case D: Stream completion summary
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            done_payload = json.dumps({
                "finish_reason": "stop",
                "model": payload.model,
                "total_sources": len(matched_chunks),
                "completion_tokens": token_count,
                "total_time_ms": elapsed_ms
            })
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception as exc:
            logger.error(f"Error during LLM streaming: {str(exc)}")
            err_payload = json.dumps({
                "error": f"LLM generation failed: {str(exc)}",
                "code": "LLM_STREAM_ERROR"
            })
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/documents")
async def list_user_documents(
    user: AuthenticatedUser = Depends(get_current_user),
    vector_svc: SupabaseVectorStore = Depends(get_vector_store)
):
    """
    Retrieves all documents associated with the authenticated tenant.
    """
    docs = await vector_svc.list_documents(user.id)
    return {"documents": docs}



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

        # Keep-alive loop to prevent Render from spinning down the free instance
        import httpx
        async def ping_self():
            try:
                # Render provides the external URL in the RENDER_EXTERNAL_URL env var
                import os
                url = os.getenv("RENDER_EXTERNAL_URL", "http://127.0.0.0:8000")
                async with httpx.AsyncClient() as client:
                    await client.get(f"{url}/")
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

        full_text = "\n\n".join(
            f"--- Page {p.page_number} ---\n{p.text}" for p in payload.pages if p.text.strip()
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




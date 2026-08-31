"""
ApexTender v2.0 - RAG Query & Real-Time SSE Streaming Router
Handles user RFP questions, executes Voyage AI embeddings, searches Supabase pgvector,
touches document retention timestamps, and streams Groq LLM responses via Server-Sent Events.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
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

router = APIRouter(prefix="/api", tags=["RAG Query & Documents"])


@router.post("/query")
async def query_rag_stream(
    request: QueryRequest,
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
        query_embedding = await embedding_svc.embed_query(request.query)
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
            filter_document_ids=request.document_ids,
            match_threshold=request.similarity_threshold,
            match_count=request.match_count
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
                query=request.query,
                context_chunks=matched_chunks,
                model=request.model
            ):
                token_count += 1
                token_payload = json.dumps({"delta": token, "text": token})
                yield f"event: token\ndata: {token_payload}\n\n"

            # Case D: Stream completion summary
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            done_payload = json.dumps({
                "finish_reason": "stop",
                "model": request.model,
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


@router.post("/documents/fallback-parse")
async def fallback_parse_ingest(
    payload: FallbackParseRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    embedding_svc: VoyageEmbeddingService = Depends(get_embedding_service),
    vector_svc: SupabaseVectorStore = Depends(get_vector_store)
):
    """
    Fallback endpoint receiving structured text extracted by browser-side PDF.js.
    """
    if not payload.extracted_text and not payload.pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extracted text or pages provided in fallback payload."
        )

    return {
        "status": "success",
        "document_id": payload.document_id,
        "message": "Fallback text accepted for ingestion.",
        "parser": payload.parser_used
    }

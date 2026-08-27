"""
Unified FastAPI Mock Application for ApexTender v2.0 E2E Testing.
Exposes complete FastAPI Backend, Supabase Edge Functions, Storage, and Database RPC interfaces
for high-fidelity opaque-box testing.
"""

import json
import time
import psutil
import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Header, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tests.mocks.mock_supabase import MockSupabaseService
from tests.mocks.mock_voyage import MockVoyageService
from tests.mocks.mock_groq import MockGroqService
from tests.mocks.mock_llamaparse import MockLlamaParseService
from tests.mocks.chunker import SemanticChunker

# ==========================================
# Pydantic Schemas
# ==========================================
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000, description="User question")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional document UUID filters")
    match_count: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum cosine similarity")
    model: str = Field(default="llama-3.3-70b-versatile", description="Groq LLM model name")

class FallbackPage(BaseModel):
    page_number: int
    text: str

class FallbackParseRequest(BaseModel):
    document_id: str
    pages: Optional[List[FallbackPage]] = None
    extracted_text: Optional[str] = None
    parser_used: Optional[str] = "pdfjs_client_fallback"

class ProcessDocumentRequest(BaseModel):
    document_id: str
    storage_path: Optional[str] = None
    source: Optional[str] = "client_upload"

class KeepForeverToggleRequest(BaseModel):
    keep_forever: bool

class StorageUploadPayload(BaseModel):
    filename: str
    content_base64: Optional[str] = None
    file_size_bytes: int
    mime_type: str = "application/pdf"
    keep_forever: bool = False

# ==========================================
# FastAPI Application Factory
# ==========================================
def create_mock_app(
    supabase_svc: Optional[MockSupabaseService] = None,
    voyage_svc: Optional[MockVoyageService] = None,
    groq_svc: Optional[MockGroqService] = None,
    llamaparse_svc: Optional[MockLlamaParseService] = None
) -> FastAPI:
    app = FastAPI(title="ApexTender v2.0 Test Pipeline", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    supabase = supabase_svc or MockSupabaseService()
    voyage = voyage_svc or MockVoyageService()
    groq = groq_svc or MockGroqService()
    llamaparse = llamaparse_svc or MockLlamaParseService()
    chunker = SemanticChunker()

    app.state.supabase = supabase
    app.state.voyage = voyage
    app.state.groq = groq
    app.state.llamaparse = llamaparse
    app.state.chunker = chunker
    app.state.start_time = time.time()

    # ==========================================
    # Auth Dependency
    # ==========================================
    async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header"
            )
        token = authorization.split(" ", 1)[1]
        try:
            payload = supabase.verify_token(token)
            return payload
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )

    # ==========================================
    # System Diagnostics & Health Endpoints
    # ==========================================
    @app.get("/health")
    async def health_check():
        process = psutil.Process()
        mem_info = process.memory_info()
        rss_mb = round(mem_info.rss / (1024 * 1024), 2)
        vms_mb = round(mem_info.vms / (1024 * 1024), 2)
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "environment": "test",
            "uptime_seconds": round(time.time() - app.state.start_time, 2),
            "memory": {
                "rss_mb": rss_mb,
                "vms_mb": vms_mb,
                "percent": round(process.memory_percent(), 2),
                "target_limit_mb": 300.0,
                "within_limits": rss_mb < 300.0
            }
        }

    @app.get("/api/system/metrics")
    async def system_metrics():
        process = psutil.Process()
        mem_info = process.memory_info()
        rss_mb = round(mem_info.rss / (1024 * 1024), 2)
        
        return {
            "memory_rss_mb": rss_mb,
            "memory_vms_mb": round(mem_info.vms / (1024 * 1024), 2),
            "cpu_percent": round(process.cpu_percent(interval=None), 2),
            "threads_count": process.num_threads(),
            "target_limit_mb": 300.0,
            "within_limits": rss_mb < 300.0
        }

    # ==========================================
    # RAG Query & SSE Streaming Endpoint
    # ==========================================
    @app.post("/api/query")
    async def query_endpoint(
        req: QueryRequest,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_id = user["sub"]
        
        # Step 1: Query embedding via Voyage AI
        try:
            embed_res = voyage.create_embeddings([req.query], input_type="query")
            query_embedding = embed_res["data"][0]["embedding"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Voyage AI embedding error: {str(e)}")

        # Step 2: Supabase pgvector RPC match_documents
        matched_chunks = supabase.match_documents(
            query_embedding=query_embedding,
            match_threshold=req.similarity_threshold,
            match_count=req.match_count,
            filter_user_id=user_id,
            filter_document_ids=req.document_ids
        )

        # Step 3: Asynchronous Touch document last_queried_at
        if matched_chunks:
            doc_ids = list(set(c["document_id"] for c in matched_chunks))
            supabase.touch_document_last_queried(doc_ids)

        # SSE Stream Generator
        async def event_generator():
            if not matched_chunks:
                error_payload = {
                    "error": "Vector search returned no relevant chunks for the selected document(s).",
                    "code": "NO_CONTEXT_FOUND"
                }
                yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                return

            # Yield sources metadata event
            sources_payload = {
                "sources": [
                    {
                        "chunk_id": c["chunk_id"],
                        "document_id": c["document_id"],
                        "file_name": c["file_name"],
                        "page_number": c["page_number"],
                        "section_header": c["section_header"],
                        "similarity": c["similarity"],
                        "snippet": c["content"][:200]
                    }
                    for c in matched_chunks
                ]
            }
            yield f"event: sources\ndata: {json.dumps(sources_payload)}\n\n"

            # Stream LLM tokens from Groq
            try:
                messages = [
                    {"role": "system", "content": "You are a professional RFP proposal assistant."},
                    {"role": "user", "content": req.query}
                ]
                async for sse_chunk in groq.stream_chat_completion(
                    messages=messages,
                    model=req.model,
                    context_chunks=matched_chunks
                ):
                    # Format as token deltas
                    if sse_chunk.startswith("data: [DONE]"):
                        yield f"event: done\ndata: {json.dumps({'finish_reason': 'stop', 'total_sources': len(matched_chunks)})}\n\n"
                    elif sse_chunk.startswith("data: "):
                        data_json = json.loads(sse_chunk[6:].strip())
                        choices = data_json.get("choices", [])
                        if choices and choices[0].get("delta", {}).get("content"):
                            token_text = choices[0]["delta"]["content"]
                            yield f"event: token\ndata: {json.dumps({'delta': token_text, 'text': token_text})}\n\n"
            except Exception as err:
                yield f"event: error\ndata: {json.dumps({'error': str(err), 'code': 'LLM_STREAM_ERROR'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # ==========================================
    # Supabase Edge Functions: Document Ingestion
    # ==========================================
    @app.post("/functions/v1/process-document")
    async def process_document_edge(
        req: ProcessDocumentRequest,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_id = user["sub"]
        doc = supabase.documents.get(req.document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Forbidden: Tenant mismatch")

        # Atomic state update to 'processing'
        supabase.update_document(req.document_id, {"status": "processing"})

        # Retrieve file from Supabase Storage
        storage_path = req.storage_path or doc["storage_path"]
        status_code, file_bytes, err = supabase.storage_download("rfp-documents", storage_path, user_id)
        if status_code != 200:
            supabase.update_document(req.document_id, {"status": "failed", "error_message": err})
            raise HTTPException(status_code=status_code, detail=err or "File download failed")

        # Send to LlamaParse
        parse_upload = llamaparse.upload_file(doc["name"], file_bytes or b"")
        if parse_upload["status_code"] == 429 or parse_upload["status_code"] == 402:
            supabase.update_document(
                req.document_id,
                {
                    "status": "awaiting_fallback_parse",
                    "error_message": parse_upload["error"]
                }
            )
            return {
                "status": "awaiting_fallback_parse",
                "document_id": req.document_id,
                "error": "rate_limit_or_quota"
            }

        job_id = parse_upload["id"]
        job_status = llamaparse.check_job_status(job_id)
        
        if job_status.get("status") == "PENDING" and llamaparse.mode == "timeout":
            supabase.update_document(
                req.document_id,
                {"status": "awaiting_fallback_parse", "error_message": "LlamaParse timeout"}
            )
            return {"status": "awaiting_fallback_parse", "document_id": req.document_id, "error": "timeout"}

        if job_status.get("status") != "SUCCESS":
            supabase.update_document(
                req.document_id,
                {"status": "awaiting_fallback_parse", "error_message": "LlamaParse parsing failed"}
            )
            return {"status": "awaiting_fallback_parse", "document_id": req.document_id, "error": "parse_failure"}

        # Fetch Markdown result
        result_data = llamaparse.get_job_result_markdown(job_id)
        markdown_text = result_data["markdown"]

        # Markdown Semantic Chunking
        chunks = chunker.chunk_markdown(markdown_text)
        if not chunks:
            # Handle empty document
            supabase.update_document(req.document_id, {"status": "processed", "total_chunks": 0})
            return {"status": "processed", "document_id": req.document_id, "chunks_count": 0}

        # Embeddings via Voyage AI (batched in slices of 64)
        chunk_texts = [c["content"] for c in chunks]
        embed_result = voyage.create_embeddings(chunk_texts, input_type="document")
        embeddings = [e["embedding"] for e in embed_result["data"]]

        # Insert chunks into Supabase pgvector
        db_chunks = []
        for i, c in enumerate(chunks):
            db_chunks.append({
                "document_id": req.document_id,
                "user_id": user_id,
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "embedding": embeddings[i],
                "token_count": c["token_count"],
                "metadata": {
                    "page_number": c["page_number"],
                    "section_header": c["section_header"],
                    "has_table": c["has_table"],
                    "parser": "llamaparse"
                }
            })
        
        inserted_count = supabase.insert_chunks(db_chunks)
        supabase.update_document(
            req.document_id,
            {"status": "processed", "total_chunks": inserted_count, "error_message": None}
        )

        return {
            "status": "processed",
            "document_id": req.document_id,
            "chunks_count": inserted_count
        }

    # ==========================================
    # Fallback Parsing Endpoint (Edge & Backend)
    # ==========================================
    @app.post("/functions/v1/ingest-fallback-text")
    @app.post("/api/documents/fallback-parse")
    async def fallback_ingest_endpoint(
        req: FallbackParseRequest,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_id = user["sub"]
        doc = supabase.documents.get(req.document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Forbidden: Tenant mismatch")

        full_text = ""
        if req.extracted_text is not None:
            full_text = req.extracted_text
        elif req.pages is not None:
            full_text = "\n\n".join([f"## Page {p.page_number}\n{p.text}" for p in req.pages])
        else:
            raise HTTPException(status_code=422, detail="No extracted text or pages provided")

        # Semantic chunking
        chunks = chunker.chunk_markdown(full_text)
        if not chunks:
            supabase.update_document(req.document_id, {"status": "processed", "total_chunks": 0})
            return {"status": "processed", "chunks_count": 0, "source": req.parser_used}

        # Embeddings
        chunk_texts = [c["content"] for c in chunks]
        embed_result = voyage.create_embeddings(chunk_texts, input_type="document")
        embeddings = [e["embedding"] for e in embed_result["data"]]

        db_chunks = []
        for i, c in enumerate(chunks):
            db_chunks.append({
                "document_id": req.document_id,
                "user_id": user_id,
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "embedding": embeddings[i],
                "token_count": c["token_count"],
                "metadata": {
                    "page_number": c["page_number"],
                    "section_header": c["section_header"],
                    "has_table": c["has_table"],
                    "parser": req.parser_used
                }
            })

        inserted_count = supabase.insert_chunks(db_chunks)
        supabase.update_document(
            req.document_id,
            {"status": "processed", "total_chunks": inserted_count, "error_message": None}
        )

        return {
            "status": "processed",
            "document_id": req.document_id,
            "chunks_count": inserted_count,
            "source": req.parser_used
        }

    # ==========================================
    # Documents Library & keep_forever Toggle
    # ==========================================
    @app.get("/api/documents")
    async def list_documents(user: Dict[str, Any] = Depends(get_current_user)):
        user_id = user["sub"]
        user_docs = [d for d in supabase.documents.values() if d["user_id"] == user_id]
        return {"documents": user_docs}

    @app.patch("/api/documents/{document_id}/keep-forever")
    @app.patch("/rest/v1/documents/{document_id}")
    async def toggle_keep_forever(
        document_id: str,
        req: KeepForeverToggleRequest,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_id = user["sub"]
        doc = supabase.documents.get(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Forbidden: Tenant mismatch")

        updated = supabase.update_document(document_id, {"keep_forever": req.keep_forever})
        return {"status": "success", "document_id": document_id, "keep_forever": updated["keep_forever"]}

    # ==========================================
    # Storage Direct Upload Endpoint (Supabase Storage emulation)
    # ==========================================
    @app.post("/storage/v1/object/{bucket_id}/{path:path}")
    async def storage_upload_endpoint(
        bucket_id: str,
        path: str,
        request: Request,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_id = user["sub"]
        data = await request.body()
        mime_type = request.headers.get("content-type", "application/pdf")
        
        res = supabase.storage_upload(
            bucket_id=bucket_id,
            path=path,
            data=data,
            mime_type=mime_type,
            user_id=user_id
        )
        if res["status_code"] != 200:
            raise HTTPException(status_code=res["status_code"], detail=res["error"])
        return res

    # ==========================================
    # Auto-Cleanup RPC Endpoint
    # ==========================================
    @app.post("/rest/v1/rpc/cleanup_stale_documents")
    async def rpc_cleanup_stale_documents(
        days: int = 30,
        simulated_now_iso: Optional[str] = None
    ):
        sim_now = None
        if simulated_now_iso:
            sim_now = datetime.datetime.fromisoformat(simulated_now_iso)
        result = supabase.cleanup_stale_documents(
            retention_interval=datetime.timedelta(days=days),
            simulated_now=sim_now
        )
        return result

    return app

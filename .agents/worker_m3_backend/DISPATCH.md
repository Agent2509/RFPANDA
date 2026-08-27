## 2026-08-27T12:13:14Z

You are the Worker assigned to Milestone 3: FastAPI Backend Engine (Voyage AI + pgvector + Groq Streaming) for ApexTender v2.0.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m3_backend`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`
Project specification path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`
Survey reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app/survey_report.md`
DB Schema reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/supabase/migrations/20260827000000_initial_rag_schema.sql`

Your exclusive write ownership:
- `backend/` (all files within `backend/`)

Your tasks:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `.agents/explorer_survey_app/survey_report.md`.
2. Implement the complete, production-grade Python FastAPI backend engine:
   - `backend/app/main.py`: FastAPI app initialization, CORS middleware, global error handling, lifecycle events, router inclusion.
   - `backend/app/config.py`: Pydantic settings loading env variables (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `VOYAGE_API_KEY`, `GROQ_API_KEY`, `CORS_ORIGINS`, `ENVIRONMENT`).
   - `backend/app/auth.py`: JWT validation middleware verifying Supabase bearer tokens (or mock token in test mode).
   - `backend/app/schemas/query.py`: Pydantic models for `QueryRequest`, `QueryResponseMetadata`, `SourceCitation`, `SystemMetrics`.
   - `backend/app/services/embedding.py`: Async Voyage AI client calling `voyage-3-lite` (1024d, `input_type: "query"`) with retry logic.
   - `backend/app/services/vector_store.py`: Supabase pgvector client calling `match_documents` RPC and `touch_document_last_queried` RPC.
   - `backend/app/services/llm.py`: Groq async streaming client (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) with structured system prompt for RFP analysis, citation extraction, and streaming token generator.
   - `backend/app/routers/query.py`: `POST /api/query` streaming endpoint emitting Server-Sent Events (SSE):
     - `event: metadata` with matched source citations
     - `event: token` with text tokens
     - `event: done` with completion summary
     - `event: error` for errors
     - Background task to invoke `touch_document_last_queried`.
   - `backend/app/routers/system.py`: `GET /health` and `GET /api/system/metrics` endpoints returning process RSS memory using `psutil` and verifying memory < 300MB.
   - `backend/requirements.txt`: Lightweight async dependencies (`fastapi`, `uvicorn`, `httpx`, `groq`, `supabase`, `pydantic`, `pydantic-settings`, `psutil`, `pytest`, `pytest-asyncio`). ZERO heavy ML packages (`torch`, `sentence-transformers`, `faiss`) to guarantee memory stays < 120MB baseline.
   - `backend/Dockerfile`: Production multi-stage Dockerfile optimized for Render free tier (<512MB RAM).
3. Create comprehensive tests in `backend/tests/`:
   - `test_memory.py`: Asserts process RSS memory is < 300MB under load.
   - `test_query.py`: Asserts `POST /api/query` SSE streaming, token chunks, citation metadata, and background touch.
   - `test_services.py`: Unit tests for embedding service, vector store client, and LLM streaming service.
   - `test_auth.py`: Unit tests for JWT authentication.
4. Run `pytest backend/tests/` and document commands, code layout, and test results in `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m3_backend/handoff.md`.
5. Send a message to parent orchestrator when complete.

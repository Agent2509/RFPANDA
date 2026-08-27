# Progress — Milestone 3: FastAPI Backend Engine

Last visited: 2026-08-27T12:17:40Z

## Status: Completed

### Completed Work
1. **Core Backend Configuration & Dependencies (`backend/requirements.txt`, `backend/app/config.py`)**:
   - Built lightweight dependency list excluding heavy ML libraries to guarantee minimal RAM (<120MB baseline).
   - Created Pydantic BaseSettings for Supabase, Voyage AI, Groq Cloud, CORS, and memory boundaries.
2. **Supabase JWT Authentication (`backend/app/auth.py`)**:
   - Implemented stateless HS256/RS256 JWT signature verification and `AuthenticatedUser` model.
   - Handled expiration, audience, subject claim enforcement, and test mode token bypass.
3. **Pydantic Schemas (`backend/app/schemas/query.py`)**:
   - Defined `QueryRequest`, `SourceCitation`, `SourcesMetadata`, `TokenDelta`, `DoneEvent`, `ErrorEvent`, `MemoryMetrics`, `HealthResponse`, `SystemMetrics`, `FallbackParseRequest`.
4. **Async Services Layer (`backend/app/services/`)**:
   - `embedding.py`: Async Voyage AI client (`voyage-3-lite`, 1024d) with exponential backoff on 429/5xx errors.
   - `vector_store.py`: Supabase pgvector client calling `match_documents` RPC and `touch_document_last_queried` RPC.
   - `llm.py`: Groq async streaming client (`llama-3.3-70b-versatile`) with structured RFP prompt and streaming token generator.
5. **API Routers & Application (`backend/app/routers/`, `backend/app/main.py`)**:
   - `system.py`: `GET /health` and `GET /api/system/metrics` with psutil memory assertions (<300MB target).
   - `query.py`: `POST /api/query` streaming SSE endpoint emitting `event: sources`, `event: token`, `event: done`, and `event: error`, with background document touch.
   - `main.py`: FastAPI app entrypoint, CORS middleware, global validation/error handlers, and connection pooling lifespan.
6. **Containerization (`backend/Dockerfile`)**:
   - Multi-stage production container running single-worker ASGI on Python 3.12-slim with non-root appuser.
7. **Comprehensive Test Suite (`backend/tests/`)**:
   - `test_memory.py`: Verified RAM < 300MB under load, zero heavy ML packages loaded in runtime.
   - `test_query.py`: Verified SSE stream events, token deltas, citation metadata, and background touch.
   - `test_services.py`: Unit tests for Voyage AI retries, pgvector search formatting, and Groq streaming.
   - `test_auth.py`: Unit tests for JWT validation, expired tokens, tampered signatures, and missing headers.
8. **Verification**:
   - Ran `pytest backend/tests/`: 24/24 passed (100%).
   - Ran `pytest tests/`: 92/92 passed (100%).

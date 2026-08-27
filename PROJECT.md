# Project: ApexTender v2.0 Production-Grade Free-Tier-Proof RAG Pipeline

## Architecture Overview
ApexTender v2.0 is an enterprise-grade, cost-optimized Retrieval-Augmented Generation (RAG) platform specifically engineered to operate reliably on free-tier cloud infrastructure (Vercel Hobby, Render Free, Supabase Free Tier, Groq Free, Voyage AI Free, LlamaParse Free).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                NEXT.JS FRONTEND (Vercel)                               │
│  - Supabase Auth (Login/Signup/Session)                                                │
│  - Direct Storage Upload (Bypasses Vercel 4.5MB Serverless Payload Limit)               │
│  - Client-Side PDF.js Fallback Parser (Zero-cost resilience on LlamaParse limits)      │
│  - Direct SSE Query Client (Bypasses Vercel 10s Serverless Execution Timeout)          │
└──────────────┬─────────────────────────────────────────────────────────▲───────────────┘
               │ Direct Browser Upload (>10MB)                           │ Direct SSE Stream
               ▼                                                         │ (<100ms TTFT)
┌──────────────────────────────────────────────┐        ┌────────────────┴───────────────┐
│         SUPABASE STORAGE & DATABASE          │        │    FASTAPI BACKEND (Render)    │
│  - Bucket: `rfp-documents` (Private + RLS)   │        │  - Stateless Async Architecture│
│  - PostgreSQL + pgvector (`vector(1024)`)    │        │  - Memory Footprint < 180MB RSS│
│  - HNSW Index (`vector_cosine_ops`)          │◄───────┤    (Strictly < 300MB target)   │
│  - `match_documents` RPC (Cosine Sim)        │ Vector │  - Voyage AI Embeddings Client │
│  - `pg_cron` Daily Stale Cleanup (30 Days)   │ Search │  - Groq API Llama 3 Streaming  │
└──────────────┬───────────────────────────────┘        └────────────────────────────────┘
               │ Storage Trigger / Webhook
               ▼
┌──────────────────────────────────────────────┐
│       SUPABASE EDGE FUNCTIONS (Deno)         │
│  - `process-document`: LlamaParse Ingestion  │
│  - `ingest-fallback-text`: PDF.js Ingestion  │
│  - Markdown-Aware Semantic Chunker           │
│  - Batched Voyage AI (1024d) Embeddings      │
└──────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Supabase Schema & Extensions | PostgreSQL extensions (`vector`, `pg_cron`, `pgcrypto`, `pg_net`), tables `documents`, `document_chunks`, `cleanup_audit_logs` | M1 | ORIGINAL_REQUEST §R4 |
| 2 | HNSW Cosine Indexing | 1024-dimensional vector indexing with `vector_cosine_ops` (`m=16`, `ef_construction=64`) | M1 | ORIGINAL_REQUEST §R4 |
| 3 | Multi-Tenant RLS Policies | Row Level Security on documents and chunks ensuring strict tenant data isolation | M1 | ORIGINAL_REQUEST §R1, R4 |
| 4 | Vector Search Stored Procedure | `match_documents` RPC with user filtering, optional doc filtering, cosine distance `<=>` | M1 | ORIGINAL_REQUEST §R2, R4 |
| 5 | Document Activity Tracking | `touch_document_last_queried` RPC updating `last_queried_at` upon retrieval matches | M1 | ORIGINAL_REQUEST §R4 |
| 6 | Automated 30-Day Cleanup Cron | `cleanup_stale_documents` procedure & `pg_cron` schedule removing stale data (< 500MB DB cap) unless `keep_forever` | M1 | ORIGINAL_REQUEST §R4 |
| 7 | Supabase Storage Configuration | Bucket `rfp-documents` with tenant paths `{user_id}/{doc_id}/{filename}` and upload policies | M2 | ORIGINAL_REQUEST §R1, R3 |
| 8 | LlamaParse Cloud Ingestion | Edge Function `process-document` calling LlamaParse for Markdown extraction | M2 | ORIGINAL_REQUEST §R3 |
| 9 | Browser PDF.js Fallback Protocol | Edge Function transitions to `awaiting_fallback_parse` on 429/402/timeout; fallback ingestion endpoint `ingest-fallback-text` | M2 | ORIGINAL_REQUEST §R3 |
| 10 | Markdown-Aware Semantic Chunker | Table-preserving recursive chunker (500–1000 tokens, 100-150 overlap) with section context | M2 | ORIGINAL_REQUEST §R3 |
| 11 | Batched Voyage AI Embeddings | Rest API client calling `voyage-3-lite` (1024d) in batches of 64 with exponential backoff | M2 | ORIGINAL_REQUEST §R3 |
| 12 | Atomic pgvector Ingestion | Batch insert chunks with vector embeddings and update document status to `processed` | M2 | ORIGINAL_REQUEST §R3 |
| 13 | Stateless FastAPI Architecture | Async FastAPI service with zero local model weights (<120MB baseline, <180MB active RSS) | M3 | ORIGINAL_REQUEST §R2 |
| 14 | Memory Monitoring & Assertion | `GET /health` & `GET /api/system/metrics` endpoints asserting RAM usage < 300MB | M3 | ORIGINAL_REQUEST §R2 |
| 15 | Voyage AI Query Embedding | 1024d embedding generation (`input_type: "query"`) for incoming user questions | M3 | ORIGINAL_REQUEST §R2 |
| 16 | Groq Llama 3 Streaming Endpoint | `POST /api/query` streaming Server-Sent Events (SSE) from Groq `llama-3.3-70b-versatile` | M3 | ORIGINAL_REQUEST §R2 |
| 17 | Source Citations & Activity Touch | Structured citation metadata emitted in stream and asynchronous `touch_document_last_queried` | M3 | ORIGINAL_REQUEST §R2 |
| 18 | Next.js App Router UI & Auth | Next.js UI with Supabase Auth (Sign in, Sign up, Session context) | M4 | ORIGINAL_REQUEST §R1 |
| 19 | Direct Browser-to-Storage Upload | Upload dropzone handling >10MB files directly to Supabase Storage (bypasses 4.5MB Vercel limit) | M4 | ORIGINAL_REQUEST §R1 |
| 20 | Client-Side PDF.js Fallback Parser | Web Worker PDF.js parser extracting text and submitting to fallback ingestion endpoint | M4 | ORIGINAL_REQUEST §R3 |
| 21 | Document Management Library | Real-time status list, `keep_forever` toggle, manual delete, file size and chunk count badges | M4 | ORIGINAL_REQUEST §R1, R4 |
| 22 | Direct-to-Backend SSE Chat UI | Markdown streaming chat interface directly connected to FastAPI backend (bypasses 10s Vercel timeout) | M4 | ORIGINAL_REQUEST §R1, R2 |
| 23 | E2E Acceptance Verification | Automated test suite verifying RAM <300MB, upload >10MB, RAG streaming, fallback parsing, pg_cron cleanup | M5 | ORIGINAL_REQUEST Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Database & pgvector + pg_cron Auto-Cleanup | Supabase SQL schema migrations, pgvector HNSW index, RLS policies, `match_documents`, `touch_document_last_queried`, `cleanup_stale_documents`, `pg_cron` schedule | None | DONE |
| 2 | Document Ingestion Pipeline | Supabase Edge Functions (`process-document`, `ingest-fallback-text`), LlamaParse client, PDF.js fallback contract, Markdown chunker, Voyage AI embedding batcher, pgvector writer | M1 | DONE |
| 3 | FastAPI Backend Engine | Stateless FastAPI service, Voyage AI query embeddings, Supabase pgvector RPC client, Groq Llama 3 SSE streaming endpoint, Memory monitoring (<300MB RAM) | M1 | DONE |
| 4 | Next.js Frontend UI | Supabase Auth, Direct Storage upload dropzone (>10MB), Client-side PDF.js fallback parser, Document Library with `keep_forever`, Direct SSE chat interface | M1, M2, M3 | DONE |
| 5 | E2E Integration & Verification | 100% E2E test pass (Tiers 1-4), acceptance criteria validation, adversarial coverage hardening (Tier 5), victory audit | M1, M2, M3, M4 | DONE |

## Interface Contracts

### 1. Database ↔ All Services (Supabase PostgreSQL)
- **Embedding Dimension**: `vector(1024)` (`voyage-3` / `voyage-3-lite`)
- **RPC `match_documents`**:
  ```sql
  FUNCTION match_documents(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.2,
    match_count int DEFAULT 5,
    filter_user_id uuid DEFAULT NULL,
    filter_document_id uuid DEFAULT NULL
  ) RETURNS TABLE (
    id uuid,
    document_id uuid,
    document_name text,
    chunk_index int,
    content text,
    similarity float,
    metadata jsonb
  )
  ```
- **RPC `touch_document_last_queried`**:
  ```sql
  FUNCTION touch_document_last_queried(p_document_ids uuid[]) RETURNS void
  ```
- **RPC `cleanup_stale_documents`**:
  ```sql
  FUNCTION cleanup_stale_documents(retention_interval interval DEFAULT interval '30 days') RETURNS jsonb
  ```

### 2. Frontend ↔ Supabase Edge Functions (Ingestion)
- **Trigger `POST /functions/v1/process-document`**:
  - Request: `{ "document_id": "uuid", "storage_path": "path" }`, Headers: `Authorization: Bearer <user_jwt>`
  - Response: `{ "status": "processed", "chunks_count": 14 }` or `{ "status": "awaiting_fallback_parse", "error": "rate_limit" }`
- **Fallback Ingestion `POST /functions/v1/ingest-fallback-text`**:
  - Request: `{ "document_id": "uuid", "text": "extracted full text..." }`, Headers: `Authorization: Bearer <user_jwt>`
  - Response: `{ "status": "processed", "chunks_count": 12, "source": "client_fallback" }`

### 3. Frontend ↔ FastAPI Backend (Query & Streaming)
- **Direct Query `POST /api/query`**:
  - Headers: `Authorization: Bearer <user_jwt>`, `Content-Type: application/json`
  - Request:
    ```json
    {
      "query": "What are the SLA penalty terms in Section 4?",
      "document_ids": ["uuid1", "uuid2"],
      "match_threshold": 0.25,
      "top_k": 5
    }
    ```
  - Response: `text/event-stream` SSE tokens:
    - `event: metadata\ndata: {"sources": [{"document_id": "...", "name": "...", "chunk_index": 2, "similarity": 0.88}]}\n\n`
    - `event: token\ndata: {"text": "According"}\n\n`
    - `event: done\ndata: {"total_tokens": 142}\n\n`
- **System Metrics `GET /api/system/metrics`**:
  - Response: `{"rss_mb": 94.2, "target_limit_mb": 300, "status": "healthy"}`

## Code Layout
```
rfp-engine/
├── .agents/                      # Agent orchestration metadata ONLY
├── supabase/
│   ├── migrations/
│   │   └── 20260827000000_initial_rag_schema.sql  # Full DDL + pgvector + pg_cron + RLS
│   ├── functions/
│   │   ├── _shared/
│   │   │   ├── chunker.ts                         # Markdown-aware table preserving chunker
│   │   │   ├── voyage.ts                          # Voyage AI 1024d embedding client
│   │   │   ├── llamaparse.ts                      # LlamaParse API client
│   │   │   └── supabase.ts                        # Deno Supabase client helper
│   │   ├── process-document/
│   │   │   └── index.ts                           # Storage ingestion Edge Function
│   │   └── ingest-fallback-text/
│   │       └── index.ts                           # Client-side PDF.js fallback ingestion
│   └── config.toml                                # Supabase local dev configuration
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                                # FastAPI app entrypoint, CORS, routes
│   │   ├── config.py                              # Pydantic settings & env validation
│   │   ├── auth.py                                # Supabase JWT validation middleware
│   │   ├── services/
│   │   │   ├── embedding.py                       # Voyage AI async client
│   │   │   ├── vector_store.py                    # Supabase pgvector RPC client
│   │   │   └── llm.py                             # Groq Llama 3 async streaming client
│   │   ├── routers/
│   │   │   ├── query.py                           # /api/query SSE streaming endpoint
│   │   │   └── system.py                          # /health and /api/system/metrics endpoints
│   │   └── schemas/
│   │       └── query.py                           # Pydantic request/response schemas
│   ├── tests/
│   │   ├── test_memory.py                         # RSS memory assertion test (<300MB)
│   │   ├── test_query.py                          # Query streaming endpoint tests
│   │   └── test_services.py                       # Unit tests for embedding, search, LLM
│   ├── requirements.txt                           # Lightweight dependencies (no torch/faiss)
│   └── Dockerfile                                 # Free-tier optimized container
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                           # Main Dashboard & RAG interface
│   │   │   ├── login/page.tsx                     # Supabase Auth login
│   │   │   └── signup/page.tsx                    # Supabase Auth signup
│   │   ├── components/
│   │   │   ├── auth/                              # Auth forms
│   │   │   ├── upload/                            # Direct Storage dropzone (>10MB bypass)
│   │   │   ├── documents/                         # Document library, status, keep_forever
│   │   │   └── chat/                              # Direct SSE streaming chat + citations
│   │   └── lib/
│   │       ├── supabase-client.ts                 # Browser Supabase client
│   │       ├── pdf-fallback.ts                    # Client-side PDF.js text extractor
│   │       └── api-client.ts                      # Direct-to-FastAPI fetch SSE reader
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.js
└── tests/
    ├── e2e/                                       # End-to-End opaque-box test suite
    ├── run_e2e_tests.sh                           # E2E test runner script
    └── mocks/                                     # Mock servers for Voyage, Groq, LlamaParse
```

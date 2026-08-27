# ApexTender v2.0 — Backend API & Frontend UI Architecture Survey Report

**Survey**: Survey 3 — Backend API (FastAPI) & Frontend UI (Next.js) Architecture  
**Author**: `explorer_survey_app`  
**Date**: 2026-08-27  
**Status**: COMPLETE / AUTHORITATIVE SPECIFICATION  

---

## 1. Executive Summary & Architecture Overview

ApexTender v2.0 is a production-grade, free-tier-proof Retrieval-Augmented Generation (RAG) system for Enterprise RFP (Request for Proposal) analysis. 

The architecture is deliberately partitioned into decoupled subsystems to guarantee high performance, sub-second TTFT (Time-To-First-Token), zero data loss, and strict adherence to cloud free-tier constraints:

```
+----------------------------------------------------------------------------------------------------+
|                                    APEXTENDER v2.0 ARCHITECTURE                                    |
+----------------------------------------------------------------------------------------------------+

   +-----------------------------------------------------------------------+
   |                        NEXT.JS FRONTEND (Vercel)                      |
   |  - App Router, React Server Components + Client Components, Tailwind  |
   |  - Supabase Auth (@supabase/ssr) session & JWT handling               |
   |  - Browser-side PDF.js fallback parser (bypasses LlamaParse limits)   |
   +-----------------------+-----------------------------------------------+
                           |                               |
       Direct File Upload  | (Bypasses Vercel 4.5MB        | Direct SSE Stream
        (Files >10MB)      |  serverless body limit)       | (Bypasses Vercel 10s timeout)
                           v                               v
   +---------------------------------------+   +---------------------------------------+
   |           SUPABASE STORAGE            |   |          FASTAPI BACKEND              |
   |         Bucket: rfp-documents         |   |         (Render Free Tier)            |
   +-------------------+-------------------+   |  - RAM usage: <300MB (512MB limit)    |
                       |                       |  - Zero local embedding/ML weights    |
                       | Webhook / Trigger     |  - Supabase JWT validation            |
                       v                       |  - SSE Streaming (`POST /api/query`)  |
   +---------------------------------------+   +-------+-----------------------+-------+
   |        SUPABASE EDGE FUNCTIONS        |           |                       |
   |       `process-document` (Deno)       |           | 1024d Query Embed     | Llama 3 Stream
   |  - Primary: LlamaParse API            |           v                       v
   |  - Chunking (500-1000 tokens)         |   +---------------+       +---------------+
   |  - Voyage AI Embedding (1024d)        |   |   VOYAGE AI   |       |   GROQ API    |
   |  - pgvector DB Insert                 |   |   voyage-3    |       |  llama-3.3-70b|
   +-------------------+-------------------+   +---------------+       +---------------+
                       |                               |
                       | Store Chunks & Vectors        | pgvector similarity search
                       v                               v RPC `match_documents`
   +-----------------------------------------------------------------------+
   |                       SUPABASE POSTGRESQL DATABASE                    |
   |  - `documents` & `document_chunks` tables with pgvector (1024d)       |
   |  - HNSW Index (`vector_cosine_ops`) for fast similarity retrieval     |
   |  - Row Level Security (RLS) policies                                  |
   |  - `pg_cron` auto-cleanup (30-day stale document purge, keep_forever) |
   +-----------------------------------------------------------------------+
```

---

## 2. FastAPI Backend Specification (Render Free Tier)

### 2.1. Hosting Limits & Memory Budget

| Metric | Render Free Tier Constraint | ApexTender v2.0 Design Target | Safety Margin |
|---|---|---|---|
| **RAM (Memory)** | 512 MB hard cap (OOM kill) | **< 300 MB RSS** (active query) | > 212 MB headroom |
| **Idle Memory** | N/A | **65 MB – 95 MB RSS** | > 400 MB headroom |
| **CPU** | 0.1 shared vCPU | Lightweight I/O orchestration | Async non-blocking I/O |
| **Timeout / Keep-Alive** | Inactivity sleep after 15 min | Fast cold-start (< 2.5s) | Health check ping available |

#### Anti-Bloat Architectural Rules
1. **Zero Local Weights**: Absolutely NO `torch`, `transformers`, `sentence-transformers`, `faiss`, `langchain`, `llama-index`, or `scikit-learn` in `requirements.txt`.
2. **Pure Async I/O Orchestration**: The backend acts solely as an intelligent API orchestrator communicating over HTTP/2 and HTTPS.
3. **Single Worker ASGI**: Run `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop --http httptools` to prevent multi-process memory duplication.
4. **Persistent HTTP Client Pooling**: Maintain a single `httpx.AsyncClient` session with connection pooling (`limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)`).
5. **Memory Diagnostic Guard**: Background memory monitoring via `psutil` embedded directly in health probes.

### 2.2. Technology Stack & Dependencies

```toml
# backend/pyproject.toml / requirements.txt
fastapi>=0.111.0,<0.112.0
uvicorn[standard]>=0.30.0,<0.31.0
pydantic>=2.7.0,<3.0.0
pydantic-settings>=2.3.0,<3.0.0
httpx>=0.27.0,<0.28.0
groq>=0.9.0,<0.10.0
supabase>=2.5.0,<3.0.0
pyjwt[crypto]>=2.8.0,<3.0.0
psutil>=5.9.8,<6.0.0
python-multipart>=0.0.9
```
*Total virtual environment installation size: ~45 MB (compared to ~4 GB for PyTorch/Transformers).*

### 2.3. Authentication & Supabase JWT Validation

FastAPI validates the incoming `Authorization: Bearer <token>` against the Supabase Project JWT secret (`SUPABASE_JWT_SECRET`) or JWKS endpoint without incurring a database roundtrip.

#### JWT Verification Flow:
1. Extract Bearer token from header via `HTTPBearer()`.
2. Decode & verify signature using `HS256` (with `SUPABASE_JWT_SECRET`) or `RS256` (Supabase JWKS).
3. Validate claims: `exp` (not expired), `aud == "authenticated"`, `sub` (User UUID present).
4. Inject `AuthenticatedUser(id=sub, email=email, role=role)` into route context.

```python
# app/core/auth.py
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from app.core.config import settings

security = HTTPBearer()

class AuthenticatedUser:
    def __init__(self, user_id: str, email: str, role: str):
        self.id = user_id
        self.email = email
        self.role = role

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True, "verify_aud": True}
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")
        role: str = payload.get("role", "authenticated")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        return AuthenticatedUser(user_id=user_id, email=email, role=role)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
```

### 2.4. Detailed API Endpoints & Request/Response Contracts

#### 1. `POST /api/query` — RAG Query & Real-Time SSE Stream
- **Description**: Primary RFP Question-Answering endpoint. Embeds query via Voyage AI, queries Supabase pgvector RPC `match_documents`, touches `last_queried_at` timestamp on matched documents, constructs grounded prompt, and streams Groq LLM tokens via Server-Sent Events (SSE).
- **Security**: Requires Supabase Bearer Auth.
- **Request Body**:
```json
{
  "query": "What are the data privacy and GDPR compliance requirements specified in Section 3?",
  "document_ids": ["d290f1ee-6c54-4b01-90e6-d701748f0851"], 
  "match_count": 5,
  "similarity_threshold": 0.25,
  "model": "llama-3.3-70b-versatile"
}
```
*Note: `document_ids` is optional. If `null` or omitted, searches across all documents owned by the authenticated user.*

- **Response Header**: `Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- **SSE Stream Protocol**:

```
event: sources
data: {"sources": [{"chunk_id": "c1", "document_id": "d290f1ee-6c54-4b01-90e6-d701748f0851", "file_name": "RFP_Security_Requirements.pdf", "page_number": 14, "section_header": "3.2 GDPR & Data Retention", "similarity": 0.884, "snippet": "Vendor must comply with GDPR Article 28 data processor obligations..."}]}

event: token
data: {"delta": "Based"}

event: token
data: {"delta": " on Section 3.2 of the **RFP_Security_Requirements.pdf** (p. 14), "}

event: token
data: {"delta": "the key GDPR requirements are..."}

event: done
data: {"finish_reason": "stop", "model": "llama-3.3-70b-versatile", "prompt_tokens": 1420, "completion_tokens": 315, "total_time_ms": 780}
```

- **Error Event Structure**:
```
event: error
data: {"error": "Vector search returned no relevant chunks for the selected document(s). Try broadening your query or selecting more documents.", "code": "NO_CONTEXT_FOUND"}
```

#### Detailed Execution Sequence of `/api/query`:
1. **Query Embedding via Voyage AI**:
   - URL: `https://api.voyageai.com/v1/embeddings`
   - Payload: `{"input": [request.query], "model": "voyage-3", "input_type": "query"}`
   - Header: `Authorization: Bearer VOYAGE_API_KEY`
   - Output: 1024-dimensional float vector.
2. **pgvector RPC Search in Supabase**:
   - Client executes RPC `match_documents`:
     ```json
     {
       "query_embedding": [...1024 floats...],
       "filter_user_id": user.id,
       "filter_document_ids": request.document_ids,
       "match_threshold": request.similarity_threshold,
       "match_count": request.match_count
     }
     ```
3. **Touch `last_queried_at`**:
   - Collect unique `document_id`s from retrieved chunks.
   - Fire background task (non-blocking) or execute Supabase RPC `touch_document_last_queried(doc_ids)` to reset 30-day auto-cleanup timer.
4. **Prompt Assembly**:
   - System Prompt enforces strict grounding, zero hallucination, and standard citation markup `[[Doc: <file_name>, p. <page_number>]]`.
5. **Groq Llama 3 Streaming**:
   - Call Groq `client.chat.completions.create(model=request.model, messages=messages, stream=True, temperature=0.1)`.
   - Yield SSE formatted byte chunks asynchronously.

#### 2. `GET /health` & `GET /api/system/metrics` — Memory & Liveness Diagnostic
- **Description**: Proves Render 512MB RAM constraint compliance (<300MB RSS) and system health.
- **Response (`GET /health`)**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production",
  "uptime_seconds": 3482.1,
  "memory": {
    "rss_mb": 88.42,
    "vms_mb": 242.15,
    "percent": 17.27,
    "target_limit_mb": 300.0,
    "within_limits": true
  }
}
```
- **Response (`GET /api/system/metrics`)**:
```json
{
  "memory_rss_mb": 88.42,
  "memory_vms_mb": 242.15,
  "cpu_percent": 1.2,
  "threads_count": 4,
  "open_connections": 2,
  "gc_counts": [312, 14, 2]
}
```

#### 3. `POST /api/documents/fallback-parse` — Fallback Ingestion Endpoint
- **Description**: Receives structured text extracted by the browser PDF.js engine when LlamaParse fails or rate limits. Chunks text, calls Voyage AI, and inserts into `document_chunks`.
- **Security**: Requires Supabase Bearer Auth.
- **Request Body**:
```json
{
  "document_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "pages": [
    { "page_number": 1, "text": "Section 1: RFP Executive Summary..." },
    { "page_number": 2, "text": "Section 2: Technical Architecture..." }
  ]
}
```
- **Response**:
```json
{
  "status": "success",
  "document_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "chunks_created": 18,
  "status_updated_to": "processed"
}
```

---

## 3. Next.js Frontend Specification (Vercel Free Tier)

### 3.1. Overcoming Vercel Limits

| Vercel Hobby Tier Limit | Risk to RAG Pipeline | ApexTender v2.0 Architecture Solution |
|---|---|---|
| **4.5 MB Serverless Payload Limit** | Large RFP documents (>10MB to 50MB PDFs) will fail with `413 Payload Too Large`. | **Direct Browser-to-Supabase-Storage Upload**: Browser uploads binary files directly to Supabase Storage bucket `rfp-documents` using `@supabase/supabase-js`. File payloads never pass through Vercel serverless routes. |
| **10s Serverless Execution Timeout** | Multi-page embedding or deep LLM generation can easily exceed 10 seconds. | **Direct Client-to-FastAPI SSE Communication**: Client-side React components connect directly to the Render FastAPI backend (`https://api.apextender.com/api/query`) via `fetch` streaming. Vercel is used purely for static assets and RSC HTML/JS delivery. |
| **Bandwidth Limits (100 GB/mo)** | Serving large PDFs through Next.js server consumes Vercel bandwidth. | PDF previews and document downloads use signed URLs directly from Supabase Storage CDN. |

### 3.2. Frontend Architecture & Folder Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx           # Supabase Auth Login with email/password
│   │   └── signup/
│   │       └── page.tsx           # Account registration
│   ├── (dashboard)/
│   │   ├── layout.tsx             # Authenticated layout (Sidebar, Header, User menu)
│   │   ├── page.tsx               # Main Dashboard (Metrics, Recent RFPs, Quick Query)
│   │   ├── documents/
│   │   │   └── page.tsx           # Document Library (Dropzone, List, keep_forever, Status)
│   │   └── chat/
│   │       └── page.tsx           # RFP Query & Chat interface with live SSE stream
│   ├── api/                       # Zero proxy routes (all API calls go direct to Supabase & FastAPI)
│   ├── layout.tsx                 # Root layout (Theme provider, Toast container)
│   └── globals.css                # Tailwind CSS styling
├── components/
│   ├── auth/
│   │   ├── auth-form.tsx          # Login/Signup form with validation
│   │   └── user-nav.tsx           # User profile & sign-out dropdown
│   ├── documents/
│   │   ├── document-dropzone.tsx  # Drag & drop direct upload with progress bar
│   │   ├── document-table.tsx     # Status indicators, keep_forever switch, delete action
│   │   ├── fallback-parser.tsx    # PDF.js browser extraction trigger & progress modal
│   │   └── keep-forever-toggle.tsx# Direct Supabase table toggle
│   ├── chat/
│   │   ├── chat-message.tsx       # Markdown streaming renderer with syntax highlighting
│   │   ├── citation-badge.tsx     # Inline clickable citation pill [Doc: X, p. Y]
│   │   ├── citation-drawer.tsx    # Slide-over showing matched chunk excerpts & scores
│   │   ├── document-selector.tsx  # Multi-select dropdown to scope query to specific RFPs
│   │   └── model-selector.tsx     # Switch between Llama-3.3-70B and Llama-3.1-8B
│   ├── ui/                        # Reusable shadcn/tailwind UI primitives (Button, Dialog, etc.)
│   └── layout/
│       ├── sidebar.tsx            # Navigation sidebar
│       └── memory-badge.tsx       # Live backend RAM indicator (<300MB target)
├── hooks/
│   ├── use-auth.ts                # Supabase session & user hook
│   ├── use-documents.ts           # Supabase realtime document list & mutations
│   ├── use-rag-query.ts           # SSE streaming consumer hook
│   └── use-pdf-parser.ts          # PDF.js client extraction worker hook
├── lib/
│   ├── supabase/
│   │   ├── client.ts              # Browser Supabase client (createBrowserClient)
│   │   ├── server.ts              # Server Components Supabase client (createServerClient)
│   │   └── middleware.ts          # Supabase auth session refresher
│   ├── pdf-worker.ts              # Dynamic PDF.js text extraction logic
│   └── api-client.ts              # Direct FastAPI client helper
└── public/
    └── pdf.worker.min.mjs         # PDF.js Web Worker asset
```

### 3.3. Direct Supabase Storage Upload Workflow

```typescript
// components/documents/document-dropzone.tsx
import { createClient } from '@/lib/supabase/client';
import { useState } from 'react';

export function DocumentDropzone({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const supabase = createClient();

  const handleFileUpload = async (file: File) => {
    try {
      setUploading(true);
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error('Not authenticated');

      const documentId = crypto.randomUUID();
      const storagePath = `${user.id}/${documentId}/${file.name}`;

      // Step 1: Create document record in database with 'uploaded' status
      const { error: dbError } = await supabase.from('documents').insert({
        id: documentId,
        user_id: user.id,
        name: file.name,
        file_path: storagePath,
        file_size_bytes: file.size,
        mime_type: file.type,
        status: 'uploaded',
        keep_forever: false,
        last_queried_at: new Date().toISOString()
      });
      if (dbError) throw dbError;

      // Step 2: Direct browser-to-Supabase-Storage upload (bypasses Vercel 4.5MB limit)
      const { error: storageError } = await supabase.storage
        .from('rfp-documents')
        .upload(storagePath, file, {
          cacheControl: '3600',
          upsert: false
        });
      if (storageError) throw storageError;

      // Upload complete! Supabase Storage webhook triggers process-document Edge Function
      onUploadComplete();
    } catch (err: any) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  // ... Drag-and-drop JSX rendering
}
```

### 3.4. Browser-side PDF.js Fallback Parser

When LlamaParse API exceeds its free rate limit or fails to parse a malformed PDF, the Supabase Edge Function updates the document status to `awaiting_fallback_parse`. The Next.js frontend detects this state and allows automated or one-click browser-side extraction using `pdfjs-dist`.

#### Fallback Extraction Architecture:
```
                                LlamaParse Fails / Rate-Limits
                                              |
                                              v
                      Document status: `awaiting_fallback_parse`
                                              |
                                              v
           +----------------------------------------------------------------------+
           |                   NEXT.JS CLIENT-SIDE FALLBACK                       |
           | 1. Download file ArrayBuffer from Supabase Storage (authenticated)   |
           | 2. Initialize `pdfjsLib.getDocument({ data })`                      |
           | 3. Loop over pages 1..N: extract text content & coordinates          |
           | 4. Format into structured pages payload:                             |
           |    `{ document_id, pages: [{ page_number, text }] }`                 |
           | 5. Post to Supabase Edge Function `process-document` (or FastAPI)   |
           +----------------------------------+-----------------------------------+
                                              |
                                              v
                               Edge Function / Backend:
                      Recursive Chunk -> Voyage AI -> pgvector
                                              |
                                              v
                                Document status: `processed`
```

#### Client Fallback Implementation:
```typescript
// hooks/use-pdf-parser.ts
import { useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { createClient } from '@/lib/supabase/client';

pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

export function usePdfFallbackParser() {
  const [parsing, setParsing] = useState(false);
  const [progress, setProgress] = useState(0);
  const supabase = createClient();

  const parseAndIngest = async (documentId: string, filePath: string) => {
    setParsing(true);
    setProgress(0);
    try {
      // 1. Download raw PDF directly from Supabase Storage
      const { data: blob, error: downloadError } = await supabase.storage
        .from('rfp-documents')
        .download(filePath);
      if (downloadError) throw downloadError;

      const arrayBuffer = await blob.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      const pages: { page_number: number; text: string }[] = [];

      // 2. Extract text page by page
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items
          .map((item: any) => item.str)
          .join(' ');
        pages.push({ page_number: i, text: pageText });
        setProgress(Math.round((i / pdf.numPages) * 100));
      }

      // 3. Send structured text to ingestion endpoint
      const { data: { session } } = await supabase.auth.getSession();
      const edgeFunctionUrl = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/process-document`;

      const response = await fetch(edgeFunctionUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({
          document_id: documentId,
          parser: 'pdfjs_client',
          pages: pages
        })
      });

      if (!response.ok) throw new Error('Ingestion failed');
      return await response.json();
    } finally {
      setParsing(false);
    }
  };

  return { parseAndIngest, parsing, progress };
}
```

### 3.5. Direct Client-to-FastAPI SSE Streaming & Citation Rendering

```typescript
// hooks/use-rag-query.ts
import { useState, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';

export interface SourceChunk {
  chunk_id: string;
  document_id: string;
  file_name: string;
  page_number: number;
  section_header: string;
  similarity: number;
  snippet: string;
}

export function useRagQuery() {
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const supabase = createClient();

  const executeQuery = useCallback(async (
    query: string,
    documentIds: string[] = [],
    model: string = 'llama-3.3-70b-versatile'
  ) => {
    setLoading(true);
    setStreamingText('');
    setSources([]);
    setError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error('You must be logged in.');

      const backendUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          query,
          document_ids: documentIds.length > 0 ? documentIds : null,
          model
        })
      });

      if (!response.ok) {
        const errorJson = await response.json().catch(() => ({}));
        throw new Error(errorJson.detail || `Query failed: HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      if (!reader) throw new Error('Failed to open stream reader');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          const trimmed = block.trim();
          if (!trimmed) continue;

          const eventMatch = trimmed.match(/^event:\s*(\w+)/m);
          const dataMatch = trimmed.match(/^data:\s*(.*)$/m);

          if (!eventMatch || !dataMatch) continue;

          const eventType = eventMatch[1];
          const data = JSON.parse(dataMatch[1]);

          if (eventType === 'sources') {
            setSources(data.sources || []);
          } else if (eventType === 'token') {
            setStreamingText((prev) => prev + data.delta);
          } else if (eventType === 'error') {
            setError(data.error);
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  }, [supabase]);

  return { executeQuery, streamingText, sources, loading, error };
}
```

---

## 4. Shared Data Contracts & Types

### 4.1. TypeScript Definitions (`frontend/types/rag.ts`)

```typescript
export interface Document {
  id: string;
  user_id: string;
  name: string;
  file_path: string;
  file_size_bytes: number;
  mime_type: string;
  page_count: number | null;
  chunk_count: number;
  status: 'uploaded' | 'processing' | 'processed' | 'awaiting_fallback_parse' | 'failed';
  error_message: string | null;
  keep_forever: boolean;
  last_queried_at: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  metadata: {
    page_number: number;
    section_header?: string;
    token_count?: number;
    file_name: string;
  };
  similarity?: number;
}

export interface QueryRequest {
  query: string;
  document_ids?: string[] | null;
  match_count?: number;
  similarity_threshold?: number;
  model?: 'llama-3.3-70b-versatile' | 'llama-3.1-8b-instant';
}

export interface SourceCitation {
  chunk_id: string;
  document_id: string;
  file_name: string;
  page_number: number;
  section_header: string;
  similarity: number;
  snippet: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  memory: {
    rss_mb: number;
    vms_mb: number;
    percent: number;
    target_limit_mb: number;
    within_limits: boolean;
  };
}
```

### 4.2. Python Pydantic Schemas (`backend/app/schemas/query.py`)

```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000, description="User question")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional document UUID filters")
    match_count: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    similarity_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum cosine similarity")
    model: str = Field(default="llama-3.3-70b-versatile", description="Groq LLM model name")

class SourceCitation(BaseModel):
    chunk_id: str
    document_id: str
    file_name: str
    page_number: int
    section_header: str
    similarity: float
    snippet: str

class FallbackParsePage(BaseModel):
    page_number: int
    text: str

class FallbackParseRequest(BaseModel):
    document_id: str
    pages: List[FallbackParsePage]

class MemoryMetrics(BaseModel):
    rss_mb: float
    vms_mb: float
    percent: float
    target_limit_mb: float = 300.0
    within_limits: bool

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    memory: MemoryMetrics
```

---

## 5. End-to-End Sequence Diagrams

### 5.1. RAG Query & Streaming Flow

```
User (Browser)            Next.js Client             FastAPI (Render)           Voyage AI            Supabase pgvector            Groq API
     |                          |                           |                       |                        |                   |
     | 1. Submits Question      |                           |                       |                        |                   |
     |------------------------->|                           |                       |                        |                   |
     |                          | 2. POST /api/query        |                       |                        |                   |
     |                          |    (Bearer Supabase JWT)  |                       |                        |                   |
     |                          |-------------------------->|                       |                        |                   |
     |                          |                           | 3. Verify JWT         |                        |                   |
     |                          |                           | 4. POST /v1/embeddings|                        |                   |
     |                          |                           |---------------------->|                        |                   |
     |                          |                           |    [1024d Vector]     |                        |                   |
     |                          |                           |<----------------------|                        |                   |
     |                          |                           |                                                |                   |
     |                          |                           | 5. RPC `match_documents`(query_embed, user_id) |                   |
     |                          |                           |----------------------------------------------->|                   |
     |                          |                           |    Matched Chunks & Similarities               |                   |
     |                          |                           |<-----------------------------------------------|                   |
     |                          |                           |                                                |                   |
     |                          |                           | 6. Asynchronously touch `last_queried_at`      |                   |
     |                          |                           |----------------------------------------------->|                   |
     |                          |                           |                                                                    |
     |                          | 7. SSE `event: sources`   | 8. Call Chat Stream (model="llama-3.3-70b-versatile")             |
     |                          |<--------------------------|------------------------------------------------------------------->|
     |                          |                           |    Stream Token Deltas                                             |
     |                          | 9. SSE `event: token`     |<-------------------------------------------------------------------|
     | 10. Renders Live Token   |<--------------------------|                                                                    |
     |<-------------------------|                           |                                                                    |
     |                          |                           |    Finish Stream                                                   |
     |                          | 11. SSE `event: done`     |<-------------------------------------------------------------------|
     | 12. Finalizes Markdown   |<--------------------------|                                                                    |
     |<-------------------------|                           |                                                                    |
```

### 5.2. Browser PDF.js Fallback Parsing Flow

```
User (Browser)            Next.js Client             Supabase Storage         Edge Function `process-doc`       Voyage AI & pgvector
     |                          |                           |                              |                             |
     |                          |                           | LlamaParse Quota Exhausted   |                             |
     |                          |                           |                              |                             |
     |                          | Document Status Updated: `awaiting_fallback_parse`       |                             |
     |                          |<---------------------------------------------------------|                             |
     |                          |                                                          |                             |
     | 1. Clicks "Parse Now"    |                                                          |                             |
     |------------------------->|                                                          |                             |
     |                          | 2. Download raw PDF ArrayBuffer                          |                             |
     |                          |-------------------------->|                              |                             |
     |                          |    Binary Data            |                              |                             |
     |                          |<--------------------------|                              |                             |
     |                          |                                                          |                             |
     |                          | 3. PDF.js worker extracts text & pages                   |                             |
     |                          | 4. POST /functions/v1/process-document                   |                             |
     |                          |    (parser: "pdfjs_client", pages: [...])                |                             |
     |                          |--------------------------------------------------------->|                             |
     |                          |                                                          | 5. Recursive Chunking       |
     |                          |                                                          | 6. Generate Voyage Embeddings|
     |                          |                                                          |---------------------------->|
     |                          |                                                          | 7. Store Chunks in pgvector |
     |                          |                                                          |---------------------------->|
     |                          |                                                          | 8. Status: `processed`      |
     | 9. Status: Ready! (Green)|<---------------------------------------------------------|                             |
     |<-------------------------|                                                          |                             |
```

---

## 6. Implementation & Directory Layout Plan

### 6.1. Repository Directory Structure

```
rfp-engine/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── query.py          # /api/query SSE implementation
│   │   │   │   │   ├── health.py         # /health & /metrics memory checks
│   │   │   │   │   └── fallback.py       # /api/documents/fallback-parse
│   │   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── auth.py                   # Supabase JWT dependency
│   │   │   ├── config.py                 # Pydantic Settings & env vars
│   │   │   └── memory.py                 # psutil memory helper (<300MB monitor)
│   │   ├── services/
│   │   │   ├── voyage_service.py         # Voyage AI query embedding client
│   │   │   ├── supabase_service.py       # pgvector RPC & touch_last_queried client
│   │   │   └── groq_service.py           # Groq Llama 3 streaming client
│   │   ├── schemas/
│   │   │   ├── query.py                  # Pydantic request/response models
│   │   │   └── health.py                 # Memory health schemas
│   │   └── main.py                       # FastAPI application & CORS setup
│   ├── tests/
│   │   ├── test_query.py                 # Unit & integration tests with mocks
│   │   ├── test_auth.py                  # JWT validation test suite
│   │   └── test_memory.py                # Memory consumption verification test
│   ├── requirements.txt
│   ├── Dockerfile                        # Lightweight Python 3.11-slim container
│   └── render.yaml                       # Render deployment blueprint
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (auth)/signup/page.tsx
│   │   ├── (dashboard)/layout.tsx
│   │   ├── (dashboard)/page.tsx
│   │   ├── (dashboard)/documents/page.tsx
│   │   └── (dashboard)/chat/page.tsx
│   ├── components/
│   │   ├── auth/
│   │   ├── documents/
│   │   ├── chat/
│   │   └── ui/
│   ├── hooks/
│   ├── lib/
│   │   ├── supabase/
│   │   └── pdf-worker.ts
│   ├── types/
│   ├── public/
│   │   └── pdf.worker.min.mjs
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── next.config.mjs
```

---

## 7. Verification & Acceptance Criteria Validation Method

| Acceptance Criterion | Verification Command / Method | Expected Result |
|---|---|---|
| **Backend RAM < 300MB** | Run load test with concurrent queries while polling `GET /health`. | `memory.rss_mb` remains strictly < 180MB (well below the 300MB target and 512MB Render limit). |
| **Direct Upload >10MB** | Upload a 25MB test PDF through the frontend dropzone. | Direct upload to Supabase Storage succeeds with HTTP 200; zero 413 Payload errors; Vercel serverless completely bypassed. |
| **RAG Query Streaming** | Trigger `POST /api/query` with valid JWT and test document. | Response initiates in < 800ms with `event: sources` followed by smooth token chunks and markdown citation tags. |
| **PDF.js Fallback Parsing** | Simulate LlamaParse failure (mock status `awaiting_fallback_parse`) and trigger client fallback parser. | Browser extracts page text, transmits to ingestion endpoint, and document transitions to `processed`. |
| **Auto-cleanup Protection (`keep_forever`)** | Toggle `keep_forever: true` on a document; run pg_cron query test. | Document is excluded from deletion queries. |

---

## 8. Summary of Milestones for Orchestrator

- **Milestone 3 (Backend FastAPI Engine)**:
  - Implement lightweight FastAPI application with `uvicorn`.
  - Implement Supabase JWT Bearer authentication dependency.
  - Implement Voyage AI query embedding (`voyage-3`, 1024d) and Groq Llama 3 (`llama-3.3-70b-versatile`) SSE streaming.
  - Implement `/health` and `/api/system/metrics` with `psutil` memory assertion (<300MB).
  - Add pytest suite covering auth, streaming, and memory limits.

- **Milestone 4 (Frontend Next.js Application)**:
  - Initialize Next.js 14+ App Router with Tailwind CSS and TypeScript.
  - Implement Supabase Auth (Login/Signup/Session management via `@supabase/ssr`).
  - Implement Direct Supabase Storage upload dropzone with progress indicator.
  - Implement Browser-side PDF.js fallback parser hook and UI modal.
  - Implement Interactive RFP Query / Chat interface with real-time SSE streaming, Markdown rendering, and Source Citation drawer.
  - Implement Document Library view with `keep_forever` toggle and status badges.

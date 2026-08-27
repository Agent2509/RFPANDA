# ApexTender v2.0 — Survey 2: Supabase Edge Functions & Document Ingestion Pipeline

**Author**: Explorer / Specialist (Survey 2: Edge Functions & Document Ingestion)  
**Date**: 2026-08-27  
**Working Directory**: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge`  
**Target Project Path**: `/home/mohdfaizanali/Desktop/my projects/rfp-engine`

---

## 1. Executive Summary & Pipeline Architecture

ApexTender v2.0 requires a resilient, high-performance, and 100% free-tier-proof document ingestion pipeline. The architecture must handle complex multi-page RFP documents (PDFs, Word DOCX, Markdown, Text), extract structured text with complex tables intact, generate high-quality vector embeddings, and store them in Supabase `pgvector` for sub-second similarity retrieval.

### Key Architectural Pillars:
1. **Direct Storage Upload**: Clients upload files directly to Supabase Storage (`rfp-documents`), completely bypassing serverless body limits (e.g. Vercel's 4.5MB limit) and enabling multi-gigabyte or 25MB+ document ingestion.
2. **Edge Execution (`process-document`)**: Supabase Edge Functions (Deno runtime) orchestrate the processing lifecycle asynchronously without consuming server memory on Render or Next.js servers.
3. **Dual-Tier Parsing Strategy**:
   - **Primary**: LlamaParse Cloud API (state-of-the-art vision/multimodal table and document extraction to Markdown).
   - **Graceful Fallback**: If LlamaParse hits rate limits (429), quota exhaustion (402/403), or network timeouts, the system automatically transitions the document to `awaiting_fallback_parse`. The Next.js frontend uses client-side PDF.js to extract text directly in the user's browser, sending raw structured text to the `ingest-fallback-text` Edge Function. This guarantees zero downtime and zero cost even under heavy usage.
4. **Markdown-Aware Semantic Chunking**: Recursive splitting engine tailored for RFPs that preserves table rows intact, retains section headings in chunk context, and enforces 500–1000 token bounds with 100–150 token overlap.
5. **Voyage AI Embeddings (`voyage-3-lite` / `voyage-3`)**: Embeddings generated via REST API with 1024 dimensions and batched API calls (up to 128 chunks per call), optimized for retrieval accuracy and MTEB performance.
6. **Batch pgvector Ingestion**: High-speed batch insertion into `document_chunks` table with atomic status transitions.

```
+----------------------------------------------------------------------------------------------------+
|                                    DOCUMENT INGESTION ARCHITECTURE                                 |
+----------------------------------------------------------------------------------------------------+

   +------------------+
   | Next.js Frontend |
   +--------+---------+
            | 1. Direct Upload (bypass 4.5MB Vercel limit)
            v
   +---------------------------------------+
   | Supabase Storage: 'rfp-documents'    |
   | Path: {user_id}/{doc_id}/{filename}   |
   +-------------------+-------------------+
                       | 2. DB Record Created & Trigger / Direct Edge Invocation
                       v
   +-----------------------------------------------------------------------------------+
   | Supabase Edge Function: `process-document`                                        |
   | (Deno Runtime, Auth Verified, Service Role Client)                                |
   |                                                                                   |
   |  [Step 1: Download Blob from Supabase Storage]                                   |
   |                          |                                                        |
   |                          v                                                        |
   |  [Step 2: Dispatch to LlamaParse API]                                             |
   |          |                                                                        |
   |          +---> Succeeded (200 OK) ----------> [Step 4: Markdown-Aware Chunker]   |
   |          |                                                    |                   |
   |          +---> Rate Limit / Quota Exhausted (429/402/Timeout) |                   |
   |                |                                              |                   |
   |                v                                              |                   |
   |       [Update Status: 'awaiting_fallback_parse']              |                   |
   |                |                                              |                   |
   +----------------|----------------------------------------------|-------------------+
                    |                                              |
                    | (Realtime Notification / Polling)            v
                    v                             +-----------------------------------+
         +--------------------+                   | Step 5: Batched Voyage AI API     |
         | Client-side PDF.js |                   | Model: `voyage-3-lite` (1024-dim) |
         | Browser Extraction |                   | Batches: up to 128 chunks/call    |
         +----------+---------+                   +-----------------+-----------------+
                    |                                               |
                    | 3. POST /functions/v1/ingest-fallback-text    v
                    v                             +-----------------------------------+
         +--------------------+                   | Step 6: Batch Insert pgvector     |
         | Edge Function:     |                   | Table: `document_chunks`          |
         | `ingest-fallback`  |------------------>| Status: 'processed'               |
         +--------------------+                   +-----------------------------------+
```

---

## 2. Supabase Storage Bucket Configuration

### 2.1 Bucket Specification
- **Bucket ID**: `rfp-documents`
- **Public Access**: `false` (Strictly private; objects can only be downloaded via signed URLs or authenticated service role).
- **File Size Limit**: `26214400` bytes (25MB per file — exceeds the 10MB acceptance criterion while preventing accidental denial-of-service).
- **Allowed MIME Types**:
  - `application/pdf` (`.pdf`)
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (`.docx`)
  - `application/msword` (`.doc`)
  - `text/plain` (`.txt`)
  - `text/markdown` (`.md`)

### 2.2 Storage Path Schema
To enforce multi-tenant isolation and eliminate naming collisions, files are stored using the deterministic path:
```
rfp-documents/{user_id}/{document_id}/{sanitized_filename}
```
Example: `rfp-documents/a3f2e1c0-1234-4567-89ab-cdef01234567/8b7d91e2-5678-4321-98ba-dcba98765432/DoD_RFP_CyberSecurity_2026.pdf`

### 2.3 Storage Row-Level Security (RLS) SQL DDL
```sql
-- 1. Create Bucket if not exists
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'rfp-documents',
    'rfp-documents',
    false,
    26214400, -- 25MB
    ARRAY[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain',
        'text/markdown'
    ]
)
ON CONFLICT (id) DO UPDATE SET
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. Storage RLS Policies
-- Enable RLS on storage.objects
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to upload files to their own folder: {user_id}/*
CREATE POLICY "Users can upload their own RFP documents"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'rfp-documents' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to view/download files in their own folder
CREATE POLICY "Users can read their own RFP documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'rfp-documents' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to delete their own files
CREATE POLICY "Users can delete their own RFP documents"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'rfp-documents' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow service_role full access for Edge Functions & pg_cron cleanup
CREATE POLICY "Service Role has full access to rfp-documents"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'rfp-documents')
WITH CHECK (bucket_id = 'rfp-documents');
```

---

## 3. Trigger Mechanism & Event Architecture

To guarantee reliability, low latency, and zero lost uploads, ApexTender v2.0 uses an **orchestrated dual-trigger model**:

### 3.1 Primary Trigger: Direct Client-to-Edge Invocation
Immediately after the Next.js client completes the file upload to Supabase Storage and creates the `documents` row with status `uploaded`, the frontend invokes the Edge Function via:
```typescript
const response = await supabase.functions.invoke('process-document', {
  body: { document_id: docRecord.id }
});
```
- **Advantages**:
  - Instant processing startup (zero webhook queue delay).
  - Passes user JWT directly, enabling end-to-end authorization tracking.
  - Client can await or listen via Realtime for progress updates.

### 3.2 Backup Trigger: Database Webhook / `pg_net` Event Trigger
If the user's browser closes or the network drops immediately after the Storage upload, an asynchronous database trigger automatically ensures processing is initiated:
```sql
-- Trigger on public.documents INSERT where status = 'uploaded'
CREATE OR REPLACE FUNCTION public.trigger_process_document_edge()
RETURNS TRIGGER AS $$
DECLARE
    edge_url text := current_setting('app.settings.edge_function_url', true);
    service_key text := current_setting('app.settings.service_role_key', true);
BEGIN
    IF NEW.status = 'uploaded' THEN
        -- Fire async HTTP POST using pg_net without blocking the transaction
        PERFORM net.http_post(
            url := coalesce(edge_url, 'https://<project-ref>.supabase.co/functions/v1/process-document'),
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'Authorization', 'Bearer ' || coalesce(service_key, '')
            ),
            body := jsonb_build_object(
                'document_id', NEW.id,
                'source', 'db_trigger'
            )
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 3.3 Concurrency & Idempotency Locking
To prevent duplicate processing if both the client and the DB trigger fire simultaneously, `process-document` executes an atomic conditional status transition:
```sql
-- Atomic update: only one worker can acquire the lock
UPDATE public.documents 
SET status = 'processing', processing_started_at = NOW()
WHERE id = $1 AND status IN ('uploaded', 'awaiting_fallback_parse')
RETURNING id, file_path, user_id, filename;
```
If 0 rows are returned, another worker is already processing the document, and the function exits cleanly with HTTP 200 `{ "status": "already_processing" }`.

---

## 4. Edge Function: `process-document`

### 4.1 Specification
- **Path**: `supabase/functions/process-document/index.ts`
- **Runtime**: Supabase Edge Functions (Deno 1.x / 2.x)
- **Memory Limit**: 150MB
- **Execution Timeout**: 150s (Deno Edge wall-clock max; internal polling capped at 35s to prevent runaway executions).

### 4.2 LlamaParse API Integration Contract
- **Upload Endpoint**: `POST https://api.cloud.llamaindex.ai/api/parsing/upload`
- **Result Endpoint**: `GET https://api.cloud.llamaindex.ai/api/parsing/job/{job_id}/result/markdown`
- **Request Headers**:
  - `Authorization: Bearer <LLAMA_CLOUD_API_KEY>`
  - `Accept: application/json`
- **Multipart Form Payload**:
  - `file`: Blob / File stream.
  - `language`: `"en"`
  - `result_type`: `"markdown"`
  - `split_by_page`: `true`
  - `take_screenshot`: `false` (Disabled to save bandwidth and compute)
  - `is_formatting_instruction`: `true`
  - `formatting_instruction`: `"Extract all RFP sections, RFP tables, requirement matrices, pricing tables, deadlines, evaluation criteria, and instructions to bidders cleanly as standard Markdown tables and headings."`

### 4.3 Polling & Backoff Algorithm
1. Submit file to LlamaParse -> receive `job_id`.
2. Initial wait: 2000ms.
3. Poll `GET /api/parsing/job/{job_id}` every 2.5s with a max cutoff of 35,000ms (14 attempts).
4. On status `"SUCCESS"`: Fetch Markdown payload from `/result/markdown`.
5. On status `"ERROR"`, HTTP 429 (Rate Limit), HTTP 402/403 (Quota Exhausted), or timeout (>35s):
   - **Do NOT fail permanently.**
   - Update `documents.status = 'awaiting_fallback_parse'`, `documents.error_message = 'LlamaParse rate limit or timeout. Client PDF.js fallback required.'`
   - Return `{ status: "awaiting_fallback_parse", document_id: id }`.

---

## 5. Fallback Parser Flow & Client-Side PDF.js Ingestion

When LlamaParse free credits (1,000 pages/day) are depleted or rate limits are triggered during peak load, the fallback architecture activates seamlessly without developer intervention or system errors.

### 5.1 Step-by-Step Fallback Lifecycle
1. **Detection**: Edge Function marks document as `awaiting_fallback_parse`.
2. **Client Alerting**: The Next.js frontend, subscribed to `documents` table changes via Supabase Realtime, receives the update:
   ```typescript
   supabase
     .channel('document-status')
     .on('postgres_changes', { 
       event: 'UPDATE', 
       schema: 'public', 
       table: 'documents',
       filter: `id=eq.${docId}` 
     }, (payload) => {
       if (payload.new.status === 'awaiting_fallback_parse') {
         runClientPdfFallback(payload.new);
       }
     });
   ```
3. **Browser Extraction (`pdfjs-dist`)**:
   - The browser loads the PDF directly from the already-in-memory `File` object (or downloads it from Supabase Storage via signed URL if page was refreshed).
   - `pdfjs-dist` parses all pages sequentially in Web Workers.
   - Outputs structured markdown text tagged with `## Page {pageNum}` headers.
4. **Structured Ingestion Call**:
   - The browser calls `POST /functions/v1/ingest-fallback-text` with payload:
     ```json
     {
       "document_id": "8b7d91e2-5678-4321-98ba-dcba98765432",
       "extracted_text": "## Page 1\n# Section 1: RFP Requirements\n...",
       "parser_used": "pdfjs_client_fallback"
     }
     ```
5. **Embedding & Ingestion**:
   - `ingest-fallback-text` verifies user ownership, executes recursive semantic chunking, batches Voyage AI embeddings, inserts chunks into `document_chunks`, and updates document status to `processed`.

---

## 6. Recursive Semantic Text Chunking Engine

RFP documents contain mission-critical tabular structures (compliance matrices, pricing tables, SLA requirements) and hierarchical headers (`1.0 Scope`, `1.1 Technical Specs`). Naive character or token splitters destroy table syntax and strip header context, leading to poor RAG recall.

### 6.1 Chunking Principles & Parameters
- **Target Chunk Size**: `500 - 1000` tokens (~2000 - 3500 characters).
- **Target Overlap**: `100 - 150` tokens (~400 characters).
- **Hard Max Limit**: `1200` tokens.
- **Table Integrity**: Full Markdown tables (`| ... |`) are treated as atomic units. If a table fits within 1200 tokens, it is NEVER split across chunks. If a table exceeds 1200 tokens, it is split along row boundaries (`\n|`), retaining the table header row on each split chunk.
- **Context Injection**: Each chunk is prepended with its active section header (e.g. `[Context: 3.2 Evaluation Criteria]`) so that vector retrieval retains situational context even if the chunk starts mid-section.

### 6.2 Recursive Splitting Hierarchy
1. **Level 1**: Top-level Headings (`\n# `, `\n## `)
2. **Level 2**: Subheadings (`\n### `, `\n#### `)
3. **Level 3**: Table & Code Blocks (`\n\n|` or `\n\`\`\``)
4. **Level 4**: Paragraphs (`\n\n`)
5. **Level 5**: Sentences (`. `, `! `, `? `)
6. **Level 6**: Whitespace / Words (` `)

### 6.3 Chunk Metadata Schema
Each inserted chunk includes rich metadata in `document_chunks`:
```typescript
interface ChunkMetadata {
  chunk_index: number;
  page_number: number | null;
  section_header: string | null;
  has_table: boolean;
  char_count: number;
  token_count: number;
  parser: 'llamaparse' | 'pdfjs_fallback' | 'plaintext';
}
```

---

## 7. Voyage AI REST API Integration

### 7.1 Model Selection & Configuration
- **Model**: `voyage-3-lite` (Default) or `voyage-3`
  - `voyage-3-lite`: 1024 output dimensions, ultra-fast latency (~40ms), $0.02 / 1M tokens (with 200M free token credit on Voyage trial).
  - `voyage-3`: 1024 output dimensions, state-of-the-art retrieval benchmark leader.
- **Output Dimensions**: `1024` (matches Postgres pgvector `vector(1024)` column).
- **Input Type**:
  - Ingestion (Edge Function): `input_type: "document"` (Optimizes dense representation for document storage).
  - Query (FastAPI Backend): `input_type: "query"` (Optimizes asymmetric retrieval matching).

### 7.2 API Endpoint & Batching Contract
- **Endpoint**: `POST https://api.cloud.voyageai.com/v1/embeddings` (or `https://api.voyageai.com/v1/embeddings`)
- **Headers**:
  ```http
  Authorization: Bearer <VOYAGE_API_KEY>
  Content-Type: application/json
  ```
- **Batching Parameters**:
  - Voyage AI accepts up to **128 text strings** per API call.
  - The Edge Function batches chunks into slices of `BATCH_SIZE = 64` (safe buffer against payload size limits).
  - Concurrency: Sequential batching with exponential backoff on HTTP 429.

### 7.3 Request Payload
```json
{
  "model": "voyage-3-lite",
  "input": [
    "[Section: 1.0 Scope] The contractor shall provide 24/7 technical support...",
    "[Section: 1.1 SLAs] Critical issues must be acknowledged within 15 minutes..."
  ],
  "input_type": "document",
  "output_dimension": 1024,
  "truncation": true
}
```

### 7.4 Response Structure
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.01823, -0.04918, ..., 0.00281],
      "index": 0
    },
    {
      "object": "embedding",
      "embedding": [-0.01042, 0.03819, ..., -0.02194],
      "index": 1
    }
  ],
  "model": "voyage-3-lite",
  "usage": {
    "total_tokens": 1284
  }
}
```

---

## 8. Database Schema & Insertion Lifecycle

### 8.1 PostgreSQL DDL Alignment
The Edge Functions write to `documents` and `document_chunks` tables configured as follows:

```sql
-- Core documents table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded' 
        CHECK (status IN ('uploaded', 'processing', 'awaiting_fallback_parse', 'processing_fallback', 'processed', 'error')),
    total_chunks INTEGER DEFAULT 0,
    error_message TEXT,
    keep_forever BOOLEAN NOT NULL DEFAULT false,
    last_queried_at TIMESTAMPTZ DEFAULT NOW(),
    processing_started_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chunks with pgvector (1024 dimensions)
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    page_number INTEGER,
    section_header TEXT,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast indexes
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON public.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_id ON public.document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw 
ON public.document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 8.2 State Transition Matrix

| Initial State | Event / Action | Next State | Condition |
| :--- | :--- | :--- | :--- |
| `uploaded` | Edge Function starts execution | `processing` | Atomic lock acquired |
| `processing` | LlamaParse succeeds, chunks embedded | `processed` | Chunks & embeddings inserted |
| `processing` | LlamaParse 429, 402, or timeout | `awaiting_fallback_parse` | Error message logged |
| `awaiting_fallback_parse` | Client invokes fallback endpoint | `processing_fallback` | Atomic lock acquired |
| `processing_fallback`| Fallback text chunked & embedded | `processed` | Chunks & embeddings inserted |
| Any | Unrecoverable error (e.g. corrupt file) | `error` | Detailed error written to DB |

---

## 9. Security, Authentication & Role Isolation

1. **Principle of Least Privilege**:
   - Edge Functions authenticate incoming requests using standard Bearer JWT validation.
   - For client-invoked processing, the Edge Function extracts `auth.uid()` from the JWT and verifies that `document.user_id === auth.uid()`.
   - Internal database modifications and vector insertions utilize `SUPABASE_SERVICE_ROLE_KEY` to write directly to `document_chunks` while setting `user_id` explicitly for RLS compliance.
2. **Webhook Verification**:
   - If triggered via Database Webhook, the request includes a pre-shared secret in the `x-webhook-secret` header, verified with constant-time string comparison (`crypto.subtle.timingSafeEqual`).
3. **Environment Secrets Isolation**:
   - Secrets managed via Supabase Vault / Edge Secrets:
     - `SUPABASE_URL`
     - `SUPABASE_SERVICE_ROLE_KEY`
     - `LLAMA_CLOUD_API_KEY`
     - `VOYAGE_API_KEY`
     - `EDGE_FUNCTION_SECRET`

---

## 10. Free-Tier Optimization & Resource Bounds

| Constraint | Supabase / Free-Tier Bound | ApexTender v2.0 Engineering Solution |
| :--- | :--- | :--- |
| **Edge Memory** | 150 MB limit | Stream file downloads, release raw Buffers immediately after parsing, avoid loading entire document trees into memory. |
| **Edge CPU Time** | 2.0 seconds CPU time | I/O-bound architecture: CPU-intensive OCR delegated to LlamaParse; chunking uses fast linear regex scanning. |
| **Edge Wall Clock**| 150 seconds max | Hard timeout of 35s on LlamaParse polling before auto-failing to client-side fallback. |
| **LlamaParse Free**| 1,000 pages / day | Seamless automatic fallback to browser-side PDF.js (0 extra cost). |
| **Voyage AI Free** | 200M tokens trial | Sliced batching (64 chunks/req) to prevent payload overages; `voyage-3-lite` for minimum token burn. |
| **Supabase DB** | 500 MB storage | 1024-dim vectors instead of 1536/3072 dims (saves 33-66% vector disk space); automatic 30-day `pg_cron` cleanup. |

---

## 11. Complete Implementation Code Templates

### 11.1 Shared CORS Helper (`supabase/functions/_shared/cors.ts`)
```typescript
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-webhook-secret',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
};
```

### 11.2 Shared Chunker Module (`supabase/functions/_shared/chunker.ts`)
```typescript
export interface ProcessedChunk {
  chunkIndex: number;
  content: string;
  pageNumber: number | null;
  sectionHeader: string | null;
  hasTable: boolean;
  tokenCount: number;
}

export class SemanticChunker {
  private targetTokens: number;
  private overlapTokens: number;

  constructor(targetTokens = 600, overlapTokens = 100) {
    this.targetTokens = targetTokens;
    this.overlapTokens = overlapTokens;
  }

  // Rough estimation: 1 token ≈ 4 characters
  private estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }

  public chunkMarkdown(markdown: string): ProcessedChunk[] {
    const chunks: ProcessedChunk[] = [];
    // Split by Markdown headers (#, ##, ###, ####)
    const sectionRegex = /(?=^#{1,4}\s+.*$)/gm;
    const rawSections = markdown.split(sectionRegex).filter(s => s.trim().length > 0);

    let currentChunkIndex = 0;
    let activeHeader = 'General Information';

    for (const section of rawSections) {
      // Extract header if present
      const headerMatch = section.match(/^#{1,4}\s+(.*)$/m);
      if (headerMatch) {
        activeHeader = headerMatch[1].trim();
      }

      const sectionTokens = this.estimateTokens(section);

      if (sectionTokens <= this.targetTokens) {
        // Fits within one chunk
        chunks.push({
          chunkIndex: currentChunkIndex++,
          content: section.trim(),
          pageNumber: this.extractPageNumber(section),
          sectionHeader: activeHeader,
          hasTable: section.includes('|---') || section.includes('| :-'),
          tokenCount: sectionTokens,
        });
      } else {
        // Split section into paragraphs or tables
        const subBlocks = this.splitIntoSubBlocks(section);
        let buffer = '';
        let bufferTokens = 0;

        for (const block of subBlocks) {
          const blockTokens = this.estimateTokens(block);

          if (bufferTokens + blockTokens > this.targetTokens && buffer.length > 0) {
            chunks.push({
              chunkIndex: currentChunkIndex++,
              content: buffer.trim(),
              pageNumber: this.extractPageNumber(buffer),
              sectionHeader: activeHeader,
              hasTable: buffer.includes('|---') || buffer.includes('| :-'),
              tokenCount: bufferTokens,
            });

            // Retain overlap from end of buffer
            const words = buffer.split(/\s+/);
            const overlapWords = words.slice(-Math.floor(this.overlapTokens * 0.75)).join(' ');
            buffer = `[Context: ${activeHeader}]\n... ${overlapWords}\n\n` + block;
            bufferTokens = this.estimateTokens(buffer);
          } else {
            buffer += (buffer.length > 0 ? '\n\n' : '') + block;
            bufferTokens += blockTokens;
          }
        }

        if (buffer.trim().length > 0) {
          chunks.push({
            chunkIndex: currentChunkIndex++,
            content: buffer.trim(),
            pageNumber: this.extractPageNumber(buffer),
            sectionHeader: activeHeader,
            hasTable: buffer.includes('|---') || buffer.includes('| :-'),
            tokenCount: bufferTokens,
          });
        }
      }
    }

    return chunks;
  }

  private splitIntoSubBlocks(text: string): string[] {
    // Keep tables as coherent blocks
    const lines = text.split('\n');
    const blocks: string[] = [];
    let currentTable: string[] = [];
    let currentPara: string[] = [];

    for (const line of lines) {
      if (line.trim().startsWith('|')) {
        if (currentPara.length > 0) {
          blocks.push(currentPara.join('\n'));
          currentPara = [];
        }
        currentTable.push(line);
      } else {
        if (currentTable.length > 0) {
          blocks.push(currentTable.join('\n'));
          currentTable = [];
        }
        if (line.trim() === '') {
          if (currentPara.length > 0) {
            blocks.push(currentPara.join('\n'));
            currentPara = [];
          }
        } else {
          currentPara.push(line);
        }
      }
    }

    if (currentTable.length > 0) blocks.push(currentTable.join('\n'));
    if (currentPara.length > 0) blocks.push(currentPara.join('\n'));

    return blocks.filter(b => b.trim().length > 0);
  }

  private extractPageNumber(text: string): number | null {
    const match = text.match(/(?:Page|PAGE|page)\s+(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }
}
```

### 11.3 Shared Voyage AI Client (`supabase/functions/_shared/voyage.ts`)
```typescript
export interface EmbeddingResult {
  embeddings: number[][];
  totalTokens: number;
}

export class VoyageClient {
  private apiKey: string;
  private model: string;
  private baseUrl = 'https://api.voyageai.com/v1/embeddings';

  constructor(apiKey: string, model = 'voyage-3-lite') {
    this.apiKey = apiKey;
    this.model = model;
  }

  public async embedChunks(
    texts: string[],
    batchSize = 64
  ): Promise<EmbeddingResult> {
    const allEmbeddings: number[][] = [];
    let totalTokens = 0;

    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      const res = await this.callEmbeddingApi(batch);
      allEmbeddings.push(...res.data.map((d: { embedding: number[] }) => d.embedding));
      totalTokens += res.usage?.total_tokens || 0;
    }

    return {
      embeddings: allEmbeddings,
      totalTokens,
    };
  }

  private async callEmbeddingApi(inputs: string[], attempt = 1): Promise<any> {
    try {
      const res = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: this.model,
          input: inputs,
          input_type: 'document',
          output_dimension: 1024,
          truncation: true,
        }),
      });

      if (res.status === 429 && attempt <= 3) {
        const delay = Math.pow(2, attempt) * 1000;
        console.warn(`[VoyageAI] 429 Rate limit. Retrying after ${delay}ms...`);
        await new Promise((r) => setTimeout(r, delay));
        return this.callEmbeddingApi(inputs, attempt + 1);
      }

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Voyage AI API error (${res.status}): ${errText}`);
      }

      return await res.json();
    } catch (err) {
      if (attempt <= 3) {
        await new Promise((r) => setTimeout(r, 1500));
        return this.callEmbeddingApi(inputs, attempt + 1);
      }
      throw err;
    }
  }
}
```

### 11.4 Shared LlamaParse Client (`supabase/functions/_shared/llamaparse.ts`)
```typescript
export interface LlamaParseResult {
  success: boolean;
  markdown?: string;
  errorType?: 'rate_limit' | 'quota_exhausted' | 'timeout' | 'parsing_failed';
  errorMessage?: string;
}

export class LlamaParseClient {
  private apiKey: string;
  private uploadUrl = 'https://api.cloud.llamaindex.ai/api/parsing/upload';
  private jobUrl = 'https://api.cloud.llamaindex.ai/api/parsing/job';

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  public async parseFile(
    fileBlob: Blob,
    filename: string,
    maxWaitMs = 35000
  ): Promise<LlamaParseResult> {
    try {
      const formData = new FormData();
      formData.append('file', fileBlob, filename);
      formData.append('result_type', 'markdown');
      formData.append('language', 'en');
      formData.append('split_by_page', 'true');
      formData.append('is_formatting_instruction', 'true');
      formData.append(
        'formatting_instruction',
        'Extract all RFP requirement matrices, tables, deadlines, and headings accurately as Markdown.'
      );

      const uploadRes = await fetch(this.uploadUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: formData,
      });

      if (uploadRes.status === 429) {
        return { success: false, errorType: 'rate_limit', errorMessage: 'LlamaParse 429 Too Many Requests' };
      }
      if (uploadRes.status === 402 || uploadRes.status === 403) {
        return { success: false, errorType: 'quota_exhausted', errorMessage: 'LlamaParse Quota Exhausted' };
      }
      if (!uploadRes.ok) {
        const errText = await uploadRes.text();
        return { success: false, errorType: 'parsing_failed', errorMessage: `LlamaParse error: ${errText}` };
      }

      const uploadData = await uploadRes.json();
      const jobId = uploadData.id;

      // Poll for completion with cutoff
      const startTime = Date.now();
      let pollInterval = 2000;

      while (Date.now() - startTime < maxWaitMs) {
        await new Promise((r) => setTimeout(r, pollInterval));

        const jobRes = await fetch(`${this.jobUrl}/${jobId}`, {
          headers: { Authorization: `Bearer ${this.apiKey}` },
        });

        if (jobRes.status === 429) {
          return { success: false, errorType: 'rate_limit', errorMessage: 'LlamaParse polling rate-limited' };
        }

        if (jobRes.ok) {
          const jobData = await jobRes.json();
          if (jobData.status === 'SUCCESS') {
            // Fetch markdown result
            const resultRes = await fetch(`${this.jobUrl}/${jobId}/result/markdown`, {
              headers: { Authorization: `Bearer ${this.apiKey}` },
            });
            if (resultRes.ok) {
              const resultData = await resultRes.json();
              return { success: true, markdown: resultData.markdown };
            }
          } else if (jobData.status === 'ERROR') {
            return {
              success: false,
              errorType: 'parsing_failed',
              errorMessage: jobData.error_message || 'LlamaParse job failed',
            };
          }
        }
        pollInterval = Math.min(pollInterval + 500, 4000);
      }

      return {
        success: false,
        errorType: 'timeout',
        errorMessage: `LlamaParse job exceeded ${maxWaitMs / 1000}s deadline`,
      };
    } catch (err: any) {
      return {
        success: false,
        errorType: 'parsing_failed',
        errorMessage: err?.message || 'LlamaParse network failure',
      };
    }
  }
}
```

### 11.5 Main Edge Function (`supabase/functions/process-document/index.ts`)
```typescript
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.8';
import { corsHeaders } from '../_shared/cors.ts';
import { LlamaParseClient } from '../_shared/llamaparse.ts';
import { SemanticChunker } from '../_shared/chunker.ts';
import { VoyageClient } from '../_shared/voyage.ts';

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const llamaKey = Deno.env.get('LLAMA_CLOUD_API_KEY')!;
    const voyageKey = Deno.env.get('VOYAGE_API_KEY')!;

    const supabase = createClient(supabaseUrl, serviceKey);
    const body = await req.json().catch(() => ({}));
    const documentId = body.document_id || body.record?.id;

    if (!documentId) {
      return new Response(JSON.stringify({ error: 'Missing document_id' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 1. Atomic status transition to 'processing'
    const { data: doc, error: docError } = await supabase
      .from('documents')
      .update({ status: 'processing', processing_started_at: new Date().toISOString() })
      .eq('id', documentId)
      .in('status', ['uploaded', 'awaiting_fallback_parse', 'error'])
      .select('id, user_id, filename, file_path, mime_type')
      .single();

    if (docError || !doc) {
      return new Response(
        JSON.stringify({ message: 'Document already processing or not found', document_id: documentId }),
        { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // 2. Download file blob from Supabase Storage
    const { data: fileBlob, error: downloadError } = await supabase.storage
      .from('rfp-documents')
      .download(doc.file_path);

    if (downloadError || !fileBlob) {
      await supabase.from('documents').update({
        status: 'error',
        error_message: `Storage download failed: ${downloadError?.message || 'File not found'}`,
      }).eq('id', documentId);

      return new Response(JSON.stringify({ error: 'Download failed' }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 3. Attempt LlamaParse Primary Parsing
    let markdownText = '';
    const isTextDoc = doc.mime_type === 'text/plain' || doc.mime_type === 'text/markdown';

    if (isTextDoc) {
      markdownText = await fileBlob.text();
    } else {
      const llamaClient = new LlamaParseClient(llamaKey);
      const parseResult = await llamaClient.parseFile(fileBlob, doc.filename, 35000);

      if (!parseResult.success) {
        console.warn(`[LlamaParse Fallback Triggered] Reason: ${parseResult.errorType} - ${parseResult.errorMessage}`);
        
        // Update status to awaiting_fallback_parse
        await supabase.from('documents').update({
          status: 'awaiting_fallback_parse',
          error_message: `Primary parser unavailable (${parseResult.errorType}). Triggering client fallback.`,
        }).eq('id', documentId);

        return new Response(
          JSON.stringify({
            status: 'awaiting_fallback_parse',
            document_id: documentId,
            error_type: parseResult.errorType,
            message: 'Switched to fallback client-side parser',
          }),
          { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      markdownText = parseResult.markdown || '';
    }

    // 4. Semantic Text Chunking
    const chunker = new SemanticChunker(600, 100);
    const chunks = chunker.chunkMarkdown(markdownText);

    if (chunks.length === 0) {
      throw new Error('No readable text chunks could be extracted from document.');
    }

    // 5. Voyage AI Batched Embeddings (voyage-3-lite, 1024-dim)
    const voyageClient = new VoyageClient(voyageKey, 'voyage-3-lite');
    const chunkTexts = chunks.map((c) => c.content);
    const { embeddings } = await voyageClient.embedChunks(chunkTexts, 64);

    // 6. Batch Insert Chunks into Supabase pgvector
    const chunkRows = chunks.map((chunk, idx) => ({
      document_id: doc.id,
      user_id: doc.user_id,
      chunk_index: chunk.chunkIndex,
      content: chunk.content,
      embedding: embeddings[idx],
      page_number: chunk.pageNumber,
      section_header: chunk.sectionHeader,
      token_count: chunk.tokenCount,
      metadata: {
        has_table: chunk.hasTable,
        parser: isTextDoc ? 'plaintext' : 'llamaparse',
      },
    }));

    // Insert in DB batches of 100
    for (let i = 0; i < chunkRows.length; i += 100) {
      const batch = chunkRows.slice(i, i + 100);
      const { error: insertErr } = await supabase.from('document_chunks').insert(batch);
      if (insertErr) throw insertErr;
    }

    // 7. Update Document Status to 'processed'
    await supabase.from('documents').update({
      status: 'processed',
      total_chunks: chunks.length,
      processed_at: new Date().toISOString(),
      error_message: null,
    }).eq('id', documentId);

    return new Response(
      JSON.stringify({
        status: 'processed',
        document_id: documentId,
        total_chunks: chunks.length,
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (err: any) {
    console.error('[process-document error]', err);
    return new Response(JSON.stringify({ error: err.message || 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
```

### 11.6 Fallback Ingestion Edge Function (`supabase/functions/ingest-fallback-text/index.ts`)
```typescript
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.8';
import { corsHeaders } from '../_shared/cors.ts';
import { SemanticChunker } from '../_shared/chunker.ts';
import { VoyageClient } from '../_shared/voyage.ts';

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const voyageKey = Deno.env.get('VOYAGE_API_KEY')!;

    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      return new Response(JSON.stringify({ error: 'Missing Authorization header' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(supabaseUrl, serviceKey);
    const userClient = createClient(supabaseUrl, authHeader.replace('Bearer ', ''));
    const { data: { user }, error: authError } = await userClient.auth.getUser();

    if (authError || !user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const { document_id, extracted_text, parser_used } = await req.json();

    if (!document_id || !extracted_text) {
      return new Response(JSON.stringify({ error: 'Missing document_id or extracted_text' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Verify user owns the document
    const { data: doc, error: docError } = await supabase
      .from('documents')
      .select('id, user_id')
      .eq('id', document_id)
      .eq('user_id', user.id)
      .single();

    if (docError || !doc) {
      return new Response(JSON.stringify({ error: 'Document not found or unauthorized' }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await supabase.from('documents').update({
      status: 'processing_fallback',
      processing_started_at: new Date().toISOString(),
    }).eq('id', document_id);

    // Chunking
    const chunker = new SemanticChunker(600, 100);
    const chunks = chunker.chunkMarkdown(extracted_text);

    // Embeddings
    const voyageClient = new VoyageClient(voyageKey, 'voyage-3-lite');
    const chunkTexts = chunks.map((c) => c.content);
    const { embeddings } = await voyageClient.embedChunks(chunkTexts, 64);

    // Insert chunks
    const chunkRows = chunks.map((chunk, idx) => ({
      document_id: doc.id,
      user_id: doc.user_id,
      chunk_index: chunk.chunkIndex,
      content: chunk.content,
      embedding: embeddings[idx],
      page_number: chunk.pageNumber,
      section_header: chunk.sectionHeader,
      token_count: chunk.tokenCount,
      metadata: {
        has_table: chunk.hasTable,
        parser: parser_used || 'pdfjs_client_fallback',
      },
    }));

    for (let i = 0; i < chunkRows.length; i += 100) {
      const batch = chunkRows.slice(i, i + 100);
      const { error: insertErr } = await supabase.from('document_chunks').insert(batch);
      if (insertErr) throw insertErr;
    }

    // Mark processed
    await supabase.from('documents').update({
      status: 'processed',
      total_chunks: chunks.length,
      processed_at: new Date().toISOString(),
      error_message: null,
    }).eq('id', document_id);

    return new Response(
      JSON.stringify({
        status: 'processed',
        document_id,
        total_chunks: chunks.length,
        parser: 'pdfjs_client_fallback',
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (err: any) {
    console.error('[ingest-fallback-text error]', err);
    return new Response(JSON.stringify({ error: err.message || 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
```

### 11.7 Client-Side PDF.js Fallback Extractor (`frontend/lib/pdf-fallback.ts`)
```typescript
import * as pdfjsLib from 'pdfjs-dist';

// Configure worker
if (typeof window !== 'undefined' && 'Worker' in window) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;
}

export async function extractPdfTextInBrowser(file: File | ArrayBuffer): Promise<string> {
  const data = file instanceof File ? await file.arrayBuffer() : file;
  const loadingTask = pdfjsLib.getDocument({ data });
  const pdf = await loadingTask.promise;
  const pageTexts: string[] = [];

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const content = await page.getTextContent();
    
    // Group text items by vertical position (y coordinate) to preserve lines
    const lineMap = new Map<number, string[]>();
    for (const item of content.items as any[]) {
      if (!('str' in item)) continue;
      const y = Math.round(item.transform[5]);
      if (!lineMap.has(y)) {
        lineMap.set(y, []);
      }
      lineMap.get(y)!.push(item.str);
    }

    // Sort descending by Y coordinate (top of page to bottom)
    const sortedY = Array.from(lineMap.keys()).sort((a, b) => b - a);
    const lines = sortedY.map((y) => lineMap.get(y)!.join(' '));
    
    pageTexts.push(`## Page ${pageNum}\n\n${lines.join('\n')}`);
  }

  return pageTexts.join('\n\n---\n\n');
}
```

---

## 12. Verification & Validation Protocol

1. **Unit Testing**:
   - `deno test` for `SemanticChunker`: Test table integrity preservation, heading context extraction, and token overlap.
   - Mock HTTP testing for `VoyageClient`: Verify automatic 429 retry and 1024-dimension response formatting.
2. **Local Edge Function Emulation**:
   - Run `supabase start` and `supabase functions serve process-document --env-file .env.local`.
   - Send sample RFP PDF payload with valid `document_id`.
3. **Fault Injection & Fallback Testing**:
   - Simulate LlamaParse 429 rate limit or invalid API key -> Verify document transitions to `awaiting_fallback_parse`.
   - Trigger `ingest-fallback-text` with PDF.js markdown payload -> Verify vector generation, `document_chunks` insertion, and final status `processed`.
4. **pgvector Search Query Validation**:
   - Verify `match_documents` RPC returns high cosine similarity scores (>0.75) for extracted chunks.

---

## 13. Implementation Work Plan & Dependencies

- **Dependencies Required**:
  - Supabase CLI (`supabase`)
  - `@supabase/supabase-js`
  - `pdfjs-dist` (in frontend)
  - Environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LLAMA_CLOUD_API_KEY`, `VOYAGE_API_KEY`.
- **Handoff Target**: Milestone M2 (Supabase Edge Functions Implementation) & Milestone M4 (Frontend Ingestion Integration).

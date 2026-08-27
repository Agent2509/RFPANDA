# Dispatch Log for explorer_survey_app

## 2026-08-27T12:04:05Z

**Context**: Survey 3: Backend API (FastAPI) & Frontend UI (Next.js) Architecture
**Task**:
1. Read `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`.
2. Investigate and specify the Backend (FastAPI) & Frontend (Next.js) architecture for ApexTender v2.0:
   - FastAPI Backend (Render free tier, 512MB RAM limit, target <300MB usage):
     - Stateless design: No local heavyweight vector DB or embedding models in memory (use REST API calls to Voyage AI and Supabase pgvector RPC).
     - Endpoints:
       - `POST /api/query`: Receives question, document_ids filter (optional), auth token. Calls Voyage AI for query embedding -> Calls Supabase `match_documents` RPC -> Builds context prompt -> Streams LLM response from Groq API (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`) using Server-Sent Events (SSE) or StreamingResponse -> Updates `last_queried_at` for matched documents.
       - `GET /health` and memory monitoring endpoint (verifying <300MB RAM).
       - Optional fallback upload/parse ingestion endpoints if needed.
     - Error handling, CORS, Supabase JWT validation.
   - Next.js Frontend (App Router, Tailwind CSS, TypeScript, Vercel free tier):
     - Supabase Auth integration (login/signup/session management).
     - Direct Supabase Storage upload from browser (bypassing Vercel's 4.5MB serverless payload limit for files >10MB).
     - Browser-side PDF.js fallback parser component: If backend/edge signals LlamaParse failure, browser extracts text with PDF.js and sends structured text to ingestion endpoint.
     - Direct API communication from client to FastAPI backend for query streaming (bypassing Vercel 10s serverless timeout).
     - UI Views: Dashboard, Document Library (with status indicators, `keep_forever` toggle, delete, upload dropzone), Interactive RFP Query / Chat interface with real-time markdown streaming and source citation tags.
3. Write your detailed findings, component architecture, API specs, and implementation plan to `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app/survey_report.md` and write `handoff.md`.
4. When finished, send a message to your parent orchestrator summarizing your findings and linking to your reports.

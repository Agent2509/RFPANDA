# BRIEFING — 2026-08-27T12:05:00Z

## Mission
Survey, design, and specify the production-grade Backend API (FastAPI on Render Free Tier, <300MB RAM) and Frontend UI (Next.js App Router on Vercel Free Tier) architecture for ApexTender v2.0 RAG pipeline.

## 🔒 My Identity
- Archetype: explorer
- Roles: Backend & Frontend Architecture Specialist
- Working directory: /home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app
- Original parent: becaab28-d2b0-4598-9ff0-d4df3c56e0a7
- Milestone: Survey 3: Backend API (FastAPI) & Frontend UI (Next.js) Architecture

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production app code directly.
- Design strictly around free-tier constraints:
  - Render free tier: 512MB RAM cap -> Target <300MB RSS memory usage. Zero local embedding/vector models in memory.
  - Vercel free tier: 4.5MB serverless payload limit & 10s execution timeout -> Direct client-to-Supabase-Storage uploads & direct client-to-FastAPI SSE query streaming.
- Supabase JWT authentication validation for both Frontend and Backend API endpoints.
- Browser-side PDF.js fallback parser when LlamaParse fails or rate limits.
- Deliver comprehensive `survey_report.md` and 5-component `handoff.md`.

## Current Parent
- Conversation ID: becaab28-d2b0-4598-9ff0-d4df3c56e0a7
- Updated: 2026-08-27T12:05:00Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `orchestrator_1/BRIEFING.md`, `explorer_survey_db/BRIEFING.md`, `explorer_survey_edge/DISPATCH.md`
- **Key findings**:
  - Full system decoupled into Next.js frontend (Vercel), FastAPI orchestration backend (Render), Supabase PostgreSQL + pgvector + pg_cron + Storage, and Edge Functions (Deno).
  - Backend is ultra-lightweight: `httpx` REST calls to Voyage AI (`voyage-3`, 1024d) and Groq API (`llama-3.3-70b-versatile`), PostgREST RPC call to `match_documents`.
  - Memory consumption on Render is constrained to 65MB–95MB baseline, <180MB active RSS (<300MB target verified via `psutil`).
  - Next.js handles direct client-side storage uploads (`@supabase/supabase-js`) bypassing Vercel's 4.5MB body limit.
  - Next.js handles direct client-side SSE streaming (`fetch` with `ReadableStream`) bypassing Vercel's 10s serverless timeout.
  - Dynamic PDF.js text extraction handles fallback parsing if LlamaParse fails.
- **Unexplored areas**: None. Complete specification delivered.

## Key Decisions Made
- Backend architecture: FastAPI with async `httpx.AsyncClient` singleton, lightweight Supabase client, zero heavy ML libraries (`torch`, `sentence-transformers`, `faiss` strictly prohibited).
- Groq streaming via SSE (`text/event-stream`) streaming token chunks and final metadata citations (chunk IDs, source doc titles, similarity scores, page numbers).
- Supabase JWT verification: Validate HS256/RS256 JWT in FastAPI using `pyjwt` with Supabase project JWT secret.
- Frontend architecture: Next.js 14+ App Router, Tailwind CSS, Lucide icons, `@supabase/ssr` / `@supabase/supabase-js`, dynamic import of `pdfjs-dist` for client fallback parsing.

## Artifact Index
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app/survey_report.md` — Detailed Survey & Architecture Report
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app/handoff.md` — 5-Component Handoff Report
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app/progress.md` — Progress tracker and liveness heartbeat

# Original User Request

## 2026-08-27T12:02:39Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

Rebuild ApexTender v2.0 as a production-grade, free-tier-proof Retrieval-Augmented Generation (RAG) pipeline. 

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine`
Integrity mode: development

## Requirements

### R1. Frontend UI (Next.js on Vercel)
Build a Next.js application that handles user authentication via Supabase Auth and allows users to upload documents directly to Supabase Storage. The frontend must communicate directly with the backend for queries to avoid Vercel's 10s serverless timeout.

### R2. Backend Engine (FastAPI on Render)
Build a lightweight Python FastAPI backend that strictly orchestrates API calls without performing heavy local compute (to survive Render's 512MB RAM limit). It must expose an endpoint to receive a query, call Voyage AI for embeddings, search Supabase pgvector, and stream an answer using Groq (Llama 3).

### R3. Document Processing (Supabase Edge Functions)
Implement Supabase Edge Functions triggered by Storage uploads. The function must send the file to LlamaParse (with a browser-side pdf.js fallback if the limit is hit), chunk the parsed text, call Voyage AI for embeddings, and store the vectors in Supabase pgvector.

### R4. Database & Auto-Cleanup (Supabase)
Configure Supabase with pgvector for vector storage. Implement a pg_cron scheduled job to automatically delete documents (and their chunks/files) that have not been queried in 30 days, unless marked "keep_forever", to prevent hitting the 500MB database limit.

## Acceptance Criteria

### Deployment & Limits
- [ ] Backend memory usage remains under 300MB during a query.
- [ ] Large file uploads (>10MB) succeed without hitting Vercel's 4.5MB body limit or crashing the backend.

### Functional
- [ ] User can authenticate, upload a document, and see it processed.
- [ ] User can ask a question and receive a streamed RAG response sourced from the uploaded document.
- [ ] The fallback parser successfully extracts text if LlamaParse fails or rate-limits.
- [ ] The auto-cleanup cron job successfully removes stale data when triggered.

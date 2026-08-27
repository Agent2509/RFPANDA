## 2026-08-27T12:23:45Z

You are the Lead Forensic Auditor assigned to the Final Victory Audit for ApexTender v2.0.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/auditor_final`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`
Project specification path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`

Your tasks:
1. Perform an exhaustive forensic integrity audit across the entire repository:
   - `supabase/`: Verify authentic SQL migrations, HNSW index, RLS policies, PL/pgSQL procedures (`match_documents`, `touch_document_last_queried`, `cleanup_stale_documents`), Deno Edge Functions (`process-document`, `ingest-fallback-text`, `_shared/`). Ensure NO mock returns or dummy SQL logic.
   - `backend/`: Verify FastAPI implementation (`app/main.py`, `app/routers/`, `app/services/`, `app/auth.py`, `app/config.py`). Ensure genuine Voyage AI REST client, Supabase RPC vector store client, Groq Llama 3 streaming token generator, and real `psutil` memory diagnostics. Ensure zero heavy ML libraries.
   - `frontend/`: Verify Next.js application (`src/app/`, `src/components/`, `src/lib/`, `src/hooks/`). Ensure genuine Supabase Auth, direct Storage upload dropzone, client-side PDF.js fallback parser, and direct SSE query reader.
   - `tests/`: Verify opaque-box E2E test suite (Tiers 1-4) in `tests/e2e/`, mock services in `tests/mocks/`, and test runner `tests/run_e2e_tests.sh`.
2. Inspect for prohibited patterns: hardcoded answers in production code, fake mock overrides, test tampering, or cheating.
3. Execute verification suites to confirm runtime authenticity.
4. Record your audit verdict: `CLEAN` or `INTEGRITY VIOLATION`.
5. Write your complete forensic audit report to `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/auditor_final/handoff.md`.
6. Send a message to the orchestrator with your verdict and evidence.

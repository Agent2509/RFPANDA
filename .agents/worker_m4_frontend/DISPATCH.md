## 2026-08-27T12:18:03Z

You are the Worker assigned to Milestone 4: Next.js Frontend UI (Supabase Auth + Direct Storage Upload + Streamed Query + Fallback Parser) for ApexTender v2.0.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m4_frontend`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`
Project specification path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`
Survey reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_app/survey_report.md`
DB Schema reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/supabase/migrations/20260827000000_initial_rag_schema.sql`

Your exclusive write ownership:
- `frontend/` (all files within `frontend/`)

Your tasks:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `.agents/explorer_survey_app/survey_report.md`.
2. Implement the complete, production-grade Next.js frontend in `frontend/`:
   - `frontend/package.json`: Dependencies (`next`, `react`, `react-dom`, `@supabase/supabase-js`, `@supabase/ssr`, `lucide-react`, `tailwindcss`, `clsx`, `tailwind-merge`, `pdfjs-dist`, `typescript`, `@types/react`, `@types/node`).
   - `frontend/tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `next.config.js`.
   - `frontend/src/lib/supabase-client.ts`: Supabase browser client configured via environment variables (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
   - `frontend/src/lib/api-client.ts`: Direct-to-FastAPI SSE streaming query client (`fetch` with `ReadableStream` reader) reading `event: sources`, `event: token`, `event: done`, `event: error`, completely bypassing Vercel's 10s serverless timeout.
   - `frontend/src/lib/pdf-fallback.ts`: Client-side PDF.js fallback parser using `pdfjs-dist` to extract structured text page by page and post to Supabase Edge Function `POST /functions/v1/ingest-fallback-text`.
   - `frontend/src/components/auth/AuthForm.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/app/signup/page.tsx`: Supabase authentication forms (email/password, sign in, sign up, session management, sign out).
   - `frontend/src/components/upload/UploadDropzone.tsx`: Drag-and-drop file uploader that uploads files (>10MB supported) directly to Supabase Storage bucket `rfp-documents` at `{user_id}/{document_id}/{filename}`, bypassing Vercel's 4.5MB payload limit, and triggers `process-document` Edge Function.
   - `frontend/src/components/documents/DocumentList.tsx`, `DocumentCard.tsx`: Document library view with real-time status badges (`uploaded`, `processing`, `awaiting_fallback_parse`, `processed`, `failed`), `keep_forever` toggle switch (calling Supabase update), manual delete button, and document selector for multi-document query scoping.
   - `frontend/src/components/chat/ChatInterface.tsx`, `MessageBubble.tsx`, `CitationDrawer.tsx`: Interactive RFP Query / Chat interface with real-time streaming tokens, Markdown rendering, copy answer, query parameter controls (threshold, top_k), and clickable source citation drawer.
   - `frontend/src/components/system/MemoryIndicator.tsx`: Free-tier health and memory badge querying FastAPI backend `/api/system/metrics` and confirming RAM < 300MB.
   - `frontend/src/app/page.tsx`, `layout.tsx`, `globals.css`: Main responsive application layout combining Sidebar/Document Library, Upload, Chat Area, and System Health.
3. Add unit and component tests (e.g. `frontend/tests/` or build verification scripts).
4. Run `npm run build` or typecheck and verify the frontend builds cleanly. Document commands, code layout, and results in `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m4_frontend/handoff.md`.
5. Send a message to parent orchestrator when complete.

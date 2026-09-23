# 🐼 RFPANDA

**Ask your documents anything — with page-level citations.**

RFPANDA is a Retrieval-Augmented Generation (RAG) web app. Upload PDFs,
DOCX, TXT or Markdown files and get grounded answers that cite the exact
document and page they came from. Every answer is generated only from your own
retrieved content — no outside knowledge, no hallucinated sources.

[![CI](https://github.com/Agent2509/RFPANDA/actions/workflows/ci.yml/badge.svg)](https://github.com/Agent2509/RFPANDA/actions/workflows/ci.yml)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.12-009688)
![Supabase](https://img.shields.io/badge/Supabase-Postgres%20%2B%20pgvector-3ecf8e)

> **Live demo:** https://rfpanda.vercel.app

---

## Features

- **Semantic search** over your documents using `pgvector` cosine similarity.
- **Grounded answers with citations** — inline `[Doc, p. X]` links and a
  citation drawer showing the exact retrieved passages and similarity scores.
- **Streaming responses** (SSE) for fast time-to-first-token.
- **Large-file uploads** straight to Supabase Storage (up to 50 MB), bypassing
  serverless body limits.
- **Resilient ingestion** — if LlamaParse rate-limits, the browser falls back to
  a client-side PDF.js parser.
- **Document library** with live status, chunk counts, per-document scope
  selection, `keep_forever` protection and manual delete.
- **Multi-tenant by design** — Supabase Row Level Security plus server-side JWT
  verification; users can only ever see their own data.
- **Free-tier friendly** — no local model weights; the backend idles around
  90–120 MB RSS with live memory telemetry at `/health`.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, Pydantic v2, async `httpx` |
| Database | Supabase Postgres + `pgvector` (1024-d, HNSW index) |
| Storage | Supabase Storage (private bucket) |
| Ingestion | Supabase Edge Functions (Deno) + LlamaParse, PDF.js fallback |
| LLM | Groq — `llama-3.3-70b-versatile` |
| Embeddings | Voyage AI — `voyage-3` (1024 dimensions) |
| CI | GitHub Actions |

---

## Quick start

**Prerequisites:** Node.js 18+, Python 3.12+, a Supabase project, and API keys
for Groq + Voyage AI. (You can run the backend in `TEST_MODE` with mock AI
responses if you don't have keys yet.)

```bash
git clone https://github.com/Agent2509/RFPANDA.git
cd RFPANDA

make setup     # creates backend/.venv, installs deps, copies .env templates
# → now edit backend/.env and frontend/.env.local with your keys

make dev       # runs backend (:8000) and frontend (:3000) together
```

Open http://localhost:3000.

<details>
<summary><strong>Manual setup (without make)</strong></summary>

```bash
# Backend
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env          # then edit

# Frontend
npm --prefix frontend install
cp frontend/.env.example frontend/.env.local  # then edit

# Run (two terminals)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
npm --prefix frontend run dev
```
</details>

### Database setup

Apply the schema to your Supabase project:

```bash
npx supabase login
npx supabase link --project-ref <your-project-ref>
npx supabase db push
```

This creates the tables, `pgvector` index, RLS policies, the search/cleanup
RPCs and the private `rfp-documents` storage bucket.

---

## Environment variables

**`backend/.env`**

| Variable | Required | Notes |
|----------|:--------:|-------|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Used for token verification fallback |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Server-side DB access |
| `SUPABASE_JWT_SECRET` | — | Only for legacy HS256 tokens; leave blank for asymmetric keys |
| `GROQ_API_KEY` | ✅ | LLM inference |
| `VOYAGE_API_KEY` | ✅ | Embeddings |
| `CORS_ORIGINS` | — | Comma-separated or JSON array; localhost + Vercel added automatically |
| `TEST_MODE` | — | `true` → deterministic mock AI (no keys needed) |
| `ENVIRONMENT` | — | `development` (default) or `production` |

**`frontend/.env.local`**

| Variable | Required | Notes |
|----------|:--------:|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | Public anon key |
| `NEXT_PUBLIC_BACKEND_URL` | ✅ | e.g. `http://localhost:8000` |

**Edge functions** — see `supabase/functions/.env.example`
(`LLAMA_CLOUD_API_KEY`, `VOYAGE_API_KEY`), applied with
`supabase secrets set --env-file supabase/functions/.env`.

---

## Common commands

```bash
make help          # list every task
make dev           # backend + frontend together
make backend       # backend only
make frontend      # frontend only
make test          # backend + frontend tests
make typecheck     # frontend TypeScript check
make build         # production frontend build
make clean         # remove caches / build output
```

---

## Project structure

```
.
├── backend/                     # FastAPI service
│   ├── app/
│   │   ├── main.py              # app factory, CORS, error handlers
│   │   ├── config.py            # Pydantic settings
│   │   ├── auth.py              # Supabase JWT verification
│   │   ├── routers/             # /api/query (SSE), /health, /api/system/*
│   │   ├── services/            # embedding, vector store, LLM, chunker
│   │   └── schemas/             # request/response models
│   └── tests/                   # pytest suite
├── frontend/                    # Next.js app
│   ├── src/app/                 # landing, login, signup, dashboard
│   ├── src/components/          # auth, upload, documents, chat, ui
│   ├── src/hooks/               # auth, documents, RAG query
│   ├── src/lib/                 # supabase client, api client, pdf fallback
│   └── tests/                   # node:test unit tests
├── supabase/
│   ├── migrations/              # SQL schema, RLS, RPCs, pg_cron
│   ├── functions/               # Deno edge functions (ingestion)
│   └── tests/                   # SQL test suite
├── tests/                       # E2E + mock-based integration suite
├── docs/                        # ARCHITECTURE.md, DEPLOYMENT.md
├── .github/workflows/           # CI + backend keep-alive
├── render.yaml                  # Render blueprint
└── Makefile
```

---

## Testing

```bash
make test                       # everything
make backend-test               # pytest backend/tests
make frontend-test              # node:test frontend/tests
```

The backend suite runs with `TEST_MODE=true` and mock transports, so it needs no
network or real API keys. The end-to-end suite lives under `tests/` and uses
mock servers for Voyage, Groq and LlamaParse.

---

## Deployment

Step-by-step instructions for Supabase, Render and Vercel — including how to
keep the free Render instance from sleeping — are in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Architecture details are in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Known limitations

- Free-tier parsers (LlamaParse) and embedding providers (Voyage AI) are
  rate-limited; very large documents may need the browser fallback or a paid
  tier to finish embedding.
- Supabase's shared SMTP rate-limits confirmation emails; use custom SMTP or
  disable email confirmation for demos.

---

## License

[MIT](LICENSE)

# 🐼 RFPanda v2.0

**Production-Grade RAG Engine for Enterprise RFP Analysis**

RFPanda is an AI-powered platform that helps teams analyze, search, and query Request for Proposal (RFP) documents using Retrieval-Augmented Generation (RAG).

## Architecture

- **Frontend**: Next.js 14 + Tailwind CSS (deployed on Vercel)
- **Backend**: FastAPI + Python 3.12 (deployed on Render Free Tier)
- **Database**: Supabase (PostgreSQL + pgvector for vector search)
- **AI Models**: Groq (LLM inference) + Voyage AI (embeddings)
- **Document Parsing**: LlamaParse (via Supabase Edge Functions)

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.12+
- Supabase account (free tier)
- API keys: Groq, Voyage AI, LlamaParse

### 1. Clone & Install
```bash
git clone https://github.com/Agent2509/RFPANDA.git
cd RFPANDA

# Frontend
cd frontend && npm install && cd ..

# Backend
cd backend && pip install -r requirements.txt && cd ..
```

### 2. Environment Variables

Copy the example files and fill in your keys:

**frontend/.env.local**
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_FASTAPI_URL=http://localhost:8000
```

**backend/.env**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
GROQ_API_KEY=your-groq-key
VOYAGE_API_KEY=your-voyage-key
```

### 3. Database Setup
```bash
npx supabase link --project-ref your-project-ref
npx supabase db push
```

### 4. Run Locally
```bash
# Terminal 1 - Backend
cd backend && uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend && npm run dev
```

Visit http://localhost:3000

## Deployment

- **Frontend → Vercel**: Connect GitHub repo, set root directory to `frontend/`
- **Backend → Render**: Uses `render.yaml` Blueprint for auto-deployment
- **Database → Supabase**: Migrations auto-applied via `supabase db push`

## License

MIT

# Deployment

This guide takes a fresh clone to a live deployment on free tiers:
**Supabase** (database + storage + edge functions), **Render** (backend) and
**Vercel** (frontend). It also explains how the backend stays awake.

---

## 1. Supabase (database, storage, edge functions)

1. Create a project at [supabase.com](https://supabase.com).
2. Grab your keys from **Project Settings → API**:
   - Project URL, `anon` key, `service_role` key.
3. Apply the schema migrations:

   ```bash
   npm i -g supabase          # or: npx supabase
   supabase login
   supabase link --project-ref <your-project-ref>
   supabase db push
   ```

   Migrations create the `documents`, `document_chunks`, `user_usage` and
   `cleanup_audit_logs` tables, the `vector`/`pgvector` index, RLS policies, the
   search/cleanup RPCs, and the private `rfp-documents` storage bucket.

4. **Auth settings → Emails.** The free shared SMTP is rate-limited
   (a few emails per hour). For a demo, either turn **off** “Confirm email”
   under **Authentication → Sign In / Providers → Email**, or connect custom
   SMTP (Resend/SendGrid/Postmark) under **Authentication → Emails**.

5. Deploy the edge functions and set their secrets:

   ```bash
   cp supabase/functions/.env.example supabase/functions/.env   # fill in values
   supabase secrets set --env-file supabase/functions/.env
   supabase functions deploy process-document
   supabase functions deploy ingest-fallback-text
   ```

---

## 2. Backend → Render

`render.yaml` at the repo root is a Blueprint.

1. Render Dashboard → **New → Blueprint** → connect the GitHub repo.
2. Set the `sync: false` environment variables (secrets):

   | Key | Value |
   |-----|-------|
   | `SUPABASE_URL` | your Supabase project URL |
   | `SUPABASE_ANON_KEY` | anon key |
   | `SUPABASE_SERVICE_ROLE_KEY` | service-role key |
   | `SUPABASE_JWT_SECRET` | leave blank if using asymmetric signing keys |
   | `GROQ_API_KEY` | Groq key |
   | `VOYAGE_API_KEY` | Voyage key |
   | `CORS_ORIGINS` | your Vercel URL, e.g. `https://your-app.vercel.app` |

   `ENVIRONMENT=production` is set in the blueprint. In production the API docs
   (`/docs`) are disabled.

3. Health check path is `/health`. First deploy takes a few minutes.

---

## 3. Frontend → Vercel

1. Vercel → **Add New → Project** → import the repo.
2. **Root Directory:** `frontend`.
3. Environment variables:

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon key |
   | `NEXT_PUBLIC_BACKEND_URL` | your Render service URL |

4. Deploy. If Supabase email confirmation is on, make sure the Site URL /
   redirect URLs include your Vercel domain.

---

## 4. Keeping the backend awake

Render’s free tier spins a web service down after ~15 minutes of inactivity, so
the first request after idle can take 30–60 s (cold start). Two options:

### Option A — GitHub Actions (included)

`.github/workflows/keepalive.yml` pings `GET /health` every 10 minutes. It works
out of the box for `https://rfpanda-backend.onrender.com/health`; change the URL
in the file if you deploy under a different name.

> GitHub pauses scheduled workflows after ~60 days of repository inactivity.
> Any push re-enables them.

### Option B — UptimeRobot (more reliable)

Create a free HTTP(s) monitor in [UptimeRobot](https://uptimerobot.com) against
`https://<your-service>.onrender.com/health` with a 5-minute interval. This also
gives you uptime alerts, which is nicer to show off.

> Render’s free tier includes 750 instance-hours/month. One always-on service
> uses ~720–744 h, so staying awake fits within the allowance.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `401` on `/api/query` or fallback | Supabase uses asymmetric signing keys and `SUPABASE_JWT_SECRET` is set to a legacy value | Leave `SUPABASE_JWT_SECRET` blank so the backend verifies via `/auth/v1/user` |
| `401` with a valid session | Backend `SUPABASE_ANON_KEY` / `SUPABASE_URL` wrong | Re-copy from Supabase → API |
| Upload works, status stuck `awaiting_fallback_parse` | LlamaParse rate limit | Use **Run fallback** in the UI |
| “email rate limit exceeded” on signup | Supabase free shared SMTP | Disable “Confirm email” or add custom SMTP |
| Fallback never finishes on huge PDFs | Voyage AI per-minute rate limits during embedding | Use smaller documents or a paid Voyage tier |
| First request is slow | Render cold start | Keep-alive workflow / UptimeRobot |

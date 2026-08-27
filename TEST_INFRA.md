# ApexTender v2.0 — End-to-End (E2E) Testing Infrastructure Documentation

**Document Version**: 2.0.0  
**Author**: E2E Testing Specialist (`test_orchestrator`)  
**Status**: ACTIVE / TEST_READY  

---

## 1. Executive Summary

The ApexTender v2.0 E2E Testing Framework provides a production-grade, 4-tier opaque-box test suite for validating all functional requirements, cloud free-tier constraints (<300MB RAM, >10MB direct uploads), resilience failovers (LlamaParse 429/402 -> PDF.js browser fallback), pgvector similarity searches, Groq Llama 3 SSE streaming, and automated `pg_cron` 30-day lifecycle retention.

All tests operate strictly against public interface contracts (HTTP REST, SSE streams, PostgreSQL RPCs, and Supabase Storage paths) without relying on internal whitebox implementations.

---

## 2. Test Suite Architecture & Directory Layout

```
tests/
├── __init__.py
├── conftest.py                             # Pytest fixtures, mock service lifecycles, auth tokens
├── test_client.py                          # High-level async test client & SSE stream consumer
├── run_e2e_tests.sh                        # Colorized, executable bash runner with exit codes
├── mocks/                                  # Lightweight deterministic mock service layer
│   ├── __init__.py
│   ├── mock_voyage.py                      # 1024-dim dense embedding generator (voyage-3-lite / voyage-3)
│   ├── mock_groq.py                        # Llama-3.3-70b-versatile SSE token streaming server
│   ├── mock_llamaparse.py                  # LlamaParse API with 429 rate limit, 402 quota & timeout emulation
│   ├── mock_supabase.py                    # Supabase Auth (JWT), Storage (rfp-documents), pgvector RPCs
│   ├── chunker.py                          # Markdown-aware table-preserving semantic chunker
│   └── mock_server_app.py                  # Unified FastAPI ASGI server orchestrating all routes
├── fixtures/                               # Realistic RFP documents and payload generators
│   ├── __init__.py
│   ├── sample_rfps.py                      # DoD Cyber Defense, Healthcare HIPAA, and Cloud Migration RFPs
│   └── document_generator.py               # Large files (>10MB-30MB), empty payloads, corrupt streams, DOCX
└── e2e/                                    # 4-Tier Test Suites (92 Test Cases)
    ├── __init__.py
    ├── test_tier1_feature_coverage.py      # Tier 1: 46 feature tests (Auth, Storage, Ingestion, Vector, Groq, keep_forever, Cron, RAM)
    ├── test_tier2_boundary_cases.py        # Tier 2: 35 boundary tests (>10MB, empty, non-PDF, malformed, 429s, 0 matches, dates)
    ├── test_tier3_cross_feature.py         # Tier 3: 7 pairwise cross-feature integration tests
    └── test_tier4_real_world_scenarios.py  # Tier 4: 4 real-world procurement & multi-tenant lifecycle scenario tests
```

---

## 3. 4-Tier Testing Methodology & Coverage Matrix

| Tier | Category | Test File | Test Count | Description |
|---|---|---|---|---|
| **Tier 1** | **Feature Coverage** | `tests/e2e/test_tier1_feature_coverage.py` | **46** | >=5 test cases per core feature in `PROJECT.md`: Supabase Auth & JWT validation, Supabase Storage uploads & RLS, LlamaParse ingestion & chunking, pgvector `match_documents` RPC cosine ranking, Groq Llama 3 SSE streaming (`POST /api/query`), `keep_forever` toggling, `cleanup_stale_documents` cron execution, and Backend RAM monitoring (<300MB RSS). |
| **Tier 2** | **Boundary & Corner Cases** | `tests/e2e/test_tier2_boundary_cases.py` | **35** | >=5 test cases per boundary dimension: >10MB/20MB uploads, 25MB bucket limits, empty 0-byte files, non-PDF formats (MD, TXT, DOCX), unsupported MIME types (415), corrupted PDF streams, malformed JSON bodies (422), negative/out-of-bounds parameters, 429 rate limit triggers, 402 quota exhaustion, polling timeouts, zero similarity matches (`NO_CONTEXT_FOUND`), regex special chars, exact 30-day retention boundaries, and custom retention intervals. |
| **Tier 3** | **Cross-Feature Integration** | `tests/e2e/test_tier3_cross_feature.py` | **7** | Pairwise end-to-end integration: Direct storage upload -> LlamaParse cloud parsing -> pgvector insertion -> vector search; LlamaParse 429 -> PDF.js fallback -> Ingestion -> Groq SSE answer; Multi-document upload & cross-document query with `touch_document_last_queried`; `keep_forever` protection during cron execution; Multi-tenant complete isolation; Concurrent multi-query streaming under memory bounds. |
| **Tier 4** | **Real-World Scenarios** | `tests/e2e/test_tier4_real_world_scenarios.py` | **4** | Full end-to-end RFP procurement lifecycles: Enterprise DoD RFP submission, table chunking, SLA penalty query, citation metadata verification, and touch refresh; State DOT Cloud Migration RFP with LlamaParse 429 and PDF.js fallback recovery; Multi-tenant enterprise zero-leakage and 35-day cron purge; High-throughput continuous RFP evaluation RAM stability (<300MB target). |
| **Total** | **All Tiers** | `tests/e2e/` | **92** | **100% Pass Rate** |

---

## 4. Deterministic Mock Service Layer

The framework includes lightweight, zero-external-dependency mock services designed for deterministic CI/CD and local test execution:

1. **`MockVoyageService`** (`tests/mocks/mock_voyage.py`):
   - Emulates Voyage AI 1024-dimensional REST API (`/v1/embeddings`).
   - Models: `voyage-3-lite`, `voyage-3`.
   - Generates deterministic L2-normalized unit vectors with word-level dense subword projections, producing realistic cosine similarities (0.6 - 0.9 for matching query-document pairs, <0.2 for unrelated content).
   - Configurable rate limiting (HTTP 429 simulation).

2. **`MockGroqService`** (`tests/mocks/mock_groq.py`):
   - Emulates Groq Cloud OpenAI-compatible chat completions streaming endpoint.
   - Models: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`.
   - Streams realistic SSE token chunks with inline citations `[[Doc: <name>, p. <page> - <section>]]` and final token usage metrics.
   - Configurable error injection (500, 429, 401).

3. **`MockLlamaParseService`** (`tests/mocks/mock_llamaparse.py`):
   - Emulates LlamaParse file upload (`POST /api/parsing/upload`), status polling (`GET /api/parsing/job/{id}`), and Markdown retrieval (`GET /api/parsing/job/{id}/result/markdown`).
   - Supports test mode flags: `success`, `429_rate_limit`, `402_quota_exhausted`, `timeout`, `parse_error`.

4. **`MockSupabaseService`** (`tests/mocks/mock_supabase.py`):
   - **Auth**: Signs and validates HS256 JWT tokens with `sub`, `email`, `role`, `aud: "authenticated"`, and expiration timestamps.
   - **Storage**: In-memory private bucket `rfp-documents` enforcing tenant folder isolation (`{user_id}/{doc_id}/{filename}`) and 25MB file size caps.
   - **Database**: PostgreSQL `documents`, `document_chunks` (with 1024d vectors), and `cleanup_audit_logs`.
   - **RPCs**: `match_documents` (cosine similarity `<=>` ranking), `touch_document_last_queried` (timestamp refresh), `cleanup_stale_documents` (cascading 30-day stale deletion and storage cleanup).

---

## 5. How to Run the Tests

### Quick Start (All Tests)
```bash
./tests/run_e2e_tests.sh
```
or via pytest:
```bash
python3 -m pytest tests/e2e -v
```

### Running Specific Tiers
```bash
# Tier 1: Feature Coverage
./tests/run_e2e_tests.sh tier1

# Tier 2: Boundary & Corner Cases
./tests/run_e2e_tests.sh tier2

# Tier 3: Cross-Feature Integration
./tests/run_e2e_tests.sh tier3

# Tier 4: Real-World Scenarios
./tests/run_e2e_tests.sh tier4
```

---

## 6. Pass/Fail Exit Codes
- Exit `0`: All tests passed successfully.
- Exit `1`: One or more test assertions failed.
- Exit `>1`: Setup or execution error.

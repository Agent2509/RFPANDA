## 2026-08-27T12:06:40Z

You are the E2E Testing Specialist assigned to the E2E Testing Track for ApexTender v2.0.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/test_orchestrator`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`
Project specification path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`

Your tasks:
1. Read `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md` and `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`.
2. Design and implement the complete E2E opaque-box test framework in `tests/` following the 4-tier methodology:
   - Tier 1: Feature Coverage (>=5 test cases per feature covering all features in PROJECT.md: auth, upload, ingestion, vector matching, groq streaming, keep_forever toggle, pg_cron cleanup, memory limit verification).
   - Tier 2: Boundary & Corner Cases (>=5 test cases per feature: large files >10MB, empty files, non-PDF formats, malformed JSON, rate limit 429 triggers, 0 similarity matches, expired vs active retention dates).
   - Tier 3: Cross-Feature Combinations (Pairwise coverage: upload + fallback parse + vector search + streaming query + keep_forever protection from cron).
   - Tier 4: Real-World Application Scenarios (Full RFP procurement lifecycle: upload enterprise RFP document, verify chunking, query complex multi-criteria RFP question, verify streaming response & citations, execute pg_cron dry-run and verify retention).
3. Create lightweight mock services or test fixtures in `tests/mocks/` (e.g. Mock Voyage AI server, Mock Groq SSE server, Mock LlamaParse server with rate-limit emulation) so the test suite can execute reliably and deterministically in local/CI environments.
4. Implement the test runner script `tests/run_e2e_tests.sh` (or pytest-based runner `python3 -m pytest tests/e2e`) with clear pass/fail exit codes.
5. Create `TEST_INFRA.md` and publish `TEST_READY.md` at the project root (`/home/mohdfaizanali/Desktop/my projects/rfp-engine/TEST_READY.md`) summarizing test counts, tier breakdown, and runner command.
6. Write a detailed handoff report in your working directory.
7. Send a message to the parent orchestrator when complete.

DO NOT CHEAT. All test implementations must be genuine opaque-box tests verifying real system entry points and contracts.

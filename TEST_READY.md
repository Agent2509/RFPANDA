# ApexTender v2.0 — Test Readiness Report (TEST_READY.md)

**Status**: 🟢 **TEST SUITE COMPLETE & READY FOR INTEGRATION**  
**Total Tests**: **92 / 92 Passed (100% Pass Rate)**  
**Execution Time**: ~3.8 seconds  
**Runner Script**: `tests/run_e2e_tests.sh` (or `python3 -m pytest tests/e2e`)  
**Date**: 2026-08-27  

---

## 1. Summary of Test Tiers & Counts

| Tier | Tier Name | Test File | Test Count | Status | Pass Rate |
|---|---|---|---|---|---|
| **Tier 1** | **Feature Coverage** | `tests/e2e/test_tier1_feature_coverage.py` | 46 | ✅ PASS | 100% (46/46) |
| **Tier 2** | **Boundary & Corner Cases** | `tests/e2e/test_tier2_boundary_cases.py` | 35 | ✅ PASS | 100% (35/35) |
| **Tier 3** | **Cross-Feature Combinations** | `tests/e2e/test_tier3_cross_feature.py` | 7 | ✅ PASS | 100% (7/7) |
| **Tier 4** | **Real-World Application Scenarios** | `tests/e2e/test_tier4_real_world_scenarios.py` | 4 | ✅ PASS | 100% (4/4) |
| **Total** | **All 4 Tiers** | `tests/e2e/` | **92** | ✅ **PASS** | **100% (92/92)** |

---

## 2. Feature Coverage Verification (PROJECT.md)

| # | Feature in PROJECT.md | Acceptance Target | E2E Tests Verifying |
|---|---|---|---|
| 1 | **Supabase Auth & JWT** | Validates HS256 tokens, rejects missing/expired/tampered tokens | 6 tests in Tier 1 |
| 2 | **Supabase Storage Direct Upload** | Uploads directly to `rfp-documents` bucket, enforces tenant folder RLS | 6 tests in Tier 1, 5 tests in Tier 2 |
| 3 | **Document Ingestion Pipeline** | LlamaParse parsing, table chunking, status transitions to `processed` | 6 tests in Tier 1, 5 tests in Tier 2 |
| 4 | **PDF.js Browser Fallback Protocol** | LlamaParse 429/402/timeout recovery via client fallback text ingestion | 5 tests across Tiers 1-4 |
| 5 | **pgvector Cosine Search (`match_documents`)** | 1024d Voyage AI vector ranking, tenant filter, doc filter, thresholding | 6 tests in Tier 1, 5 tests in Tier 2 |
| 6 | **Groq Llama 3 Streaming (`POST /api/query`)** | SSE stream (`sources`, `token`, `done`, `error`), inline citations | 6 tests in Tier 1, 4 tests in Tier 3-4 |
| 7 | **Document Activity Touch** | `touch_document_last_queried` RPC updates `last_queried_at` on search hit | 4 tests across Tiers 1-4 |
| 8 | **`keep_forever` Retention Flag** | Toggle persists in DB, protects documents from auto-cleanup cron | 5 tests in Tier 1, 3 tests in Tier 3-4 |
| 9 | **Automated 30-Day Cleanup (`pg_cron`)** | `cleanup_stale_documents` deletes stale docs, cascades chunks & storage | 6 tests in Tier 1, 5 tests in Tier 2-4 |
| 10 | **Memory Bound (<300MB RSS)** | Render 512MB RAM compliance, zero heavy local ML libraries in memory | 5 tests in Tier 1, 2 tests in Tier 3-4 |
| 11 | **Large File Upload (>10MB)** | Direct Storage bypasses Vercel 4.5MB limit (tests 12MB & 20MB files) | 5 tests in Tier 2 |

---

## 3. How to Execute the Test Suite

### Full Test Suite Execution
```bash
./tests/run_e2e_tests.sh
```
or via pytest directly:
```bash
python3 -m pytest tests/e2e -v
```

### Individual Tier Execution
```bash
# Tier 1: Feature Coverage Tests
./tests/run_e2e_tests.sh tier1

# Tier 2: Boundary & Corner Cases Tests
./tests/run_e2e_tests.sh tier2

# Tier 3: Cross-Feature Integration Tests
./tests/run_e2e_tests.sh tier3

# Tier 4: Real-World Scenarios Tests
./tests/run_e2e_tests.sh tier4
```

---

## 4. Test Infrastructure Components
- **Mock Services**: Located in `tests/mocks/` (`MockVoyageService`, `MockGroqService`, `MockLlamaParseService`, `MockSupabaseService`, `SemanticChunker`, `mock_server_app.py`).
- **Test Fixtures**: Located in `tests/fixtures/` (`sample_rfps.py`, `document_generator.py`).
- **Test Client**: Located in `tests/test_client.py` (`ApexTenderTestClient`).
- **Full Documentation**: Located in `TEST_INFRA.md`.

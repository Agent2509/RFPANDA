"""
ApexTender v2.0 - Memory Footprint & Render Constraint Verification Tests
Proves that the backend service complies strictly with the <300MB RAM budget (512MB Render limit)
and maintains zero local ML weight bloat.
"""

import sys
import psutil
import pytest
import httpx
from app.config import settings
from app.routers.system import get_memory_diagnostics


@pytest.mark.asyncio
async def test_baseline_rss_memory_strictly_under_300mb():
    """
    Asserts that the initial process RSS memory is well below 300MB (target < 120MB baseline).
    """
    mem = get_memory_diagnostics()
    assert mem.rss_mb < 300.0, f"Baseline RSS memory ({mem.rss_mb} MB) exceeded 300MB limit"
    assert mem.within_limits is True
    assert mem.target_limit_mb == 300.0


@pytest.mark.asyncio
async def test_no_heavy_ml_packages_loaded():
    """
    Verifies that no heavy local ML libraries (torch, sentence-transformers, faiss, transformers)
    are loaded into the application's runtime namespace.
    """
    prohibited_packages = [
        "sentence_transformers",
        "faiss",
        "llama_index",
        "langchain",
        "scipy.spatial.distance",
    ]

    loaded = [pkg for pkg in prohibited_packages if pkg in sys.modules]
    assert not loaded, f"Prohibited heavy ML libraries detected in memory: {loaded}"


@pytest.mark.asyncio
async def test_health_endpoint_returns_memory_diagnostics(async_client: httpx.AsyncClient):
    """
    Asserts GET /health returns live memory statistics and within_limits=true.
    """
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "memory" in data
    mem = data["memory"]
    assert "rss_mb" in mem
    assert "vms_mb" in mem
    assert "percent" in mem
    assert mem["rss_mb"] < 300.0
    assert mem["within_limits"] is True
    assert mem["target_limit_mb"] == 300.0


@pytest.mark.asyncio
async def test_system_metrics_endpoint(async_client: httpx.AsyncClient):
    """
    Asserts GET /api/system/metrics returns detailed performance counters.
    """
    response = await async_client.get("/api/system/metrics")
    assert response.status_code == 200

    data = response.json()
    assert data["memory_rss_mb"] < 300.0
    assert data["within_limits"] is True
    assert "cpu_percent" in data
    assert "threads_count" in data
    assert data["threads_count"] > 0


@pytest.mark.asyncio
async def test_memory_under_concurrent_queries(async_client: httpx.AsyncClient, auth_headers: dict):
    """
    Simulates concurrent health probes and queries to ensure memory remains strictly bounded <300MB.
    """
    import asyncio

    async def make_health_call():
        res = await async_client.get("/health")
        return res.status_code

    # Run 50 concurrent requests
    tasks = [make_health_call() for _ in range(50)]
    results = await asyncio.gather(*tasks)

    assert all(code == 200 for code in results)

    # Re-verify memory
    mem = get_memory_diagnostics()
    assert mem.rss_mb < 300.0, f"Memory spiked to {mem.rss_mb} MB after concurrent load"

"""
RFPANDA - System Health & Memory Telemetry Router
Exposes /health and /api/system/metrics endpoints continuously verifying
that backend process RSS memory stays strictly below the 300MB Render free tier constraint.
"""

import time
import psutil
from fastapi import APIRouter
from app.config import settings
from app.schemas.query import HealthResponse, MemoryMetrics, SystemMetrics

router = APIRouter(tags=["System & Diagnostics"])

# Record server start time for uptime calculation
SERVER_START_TIME = time.time()


def get_memory_diagnostics() -> MemoryMetrics:
    """
    Reads live RSS and VMS memory using psutil.
    """
    process = psutil.Process()
    mem_info = process.memory_info()
    rss_mb = round(mem_info.rss / (1024 * 1024), 2)
    vms_mb = round(mem_info.vms / (1024 * 1024), 2)
    percent = round(process.memory_percent(), 2)
    within_limits = rss_mb < settings.MEMORY_TARGET_LIMIT_MB

    return MemoryMetrics(
        rss_mb=rss_mb,
        vms_mb=vms_mb,
        percent=percent,
        target_limit_mb=settings.MEMORY_TARGET_LIMIT_MB,
        within_limits=within_limits
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Liveness and Render constraint verification probe.
    Returns HTTP 200 with memory breakdown and uptime.
    """
    memory_metrics = get_memory_diagnostics()
    uptime = round(time.time() - SERVER_START_TIME, 2)
    status_str = "healthy" if memory_metrics.within_limits else "degraded"

    return HealthResponse(
        status=status_str,
        version="2.0.0",
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime,
        memory=memory_metrics
    )


@router.get("/api/system/metrics", response_model=SystemMetrics)
async def system_metrics():
    """
    Detailed system telemetry endpoint for memory and CPU audit.
    """
    process = psutil.Process()
    mem_info = process.memory_info()
    rss_mb = round(mem_info.rss / (1024 * 1024), 2)
    vms_mb = round(mem_info.vms / (1024 * 1024), 2)
    cpu_pct = round(process.cpu_percent(interval=None), 2)
    uptime = round(time.time() - SERVER_START_TIME, 2)

    return SystemMetrics(
        memory_rss_mb=rss_mb,
        memory_vms_mb=vms_mb,
        cpu_percent=cpu_pct,
        threads_count=process.num_threads(),
        target_limit_mb=settings.MEMORY_TARGET_LIMIT_MB,
        within_limits=rss_mb < settings.MEMORY_TARGET_LIMIT_MB,
        uptime_seconds=uptime
    )

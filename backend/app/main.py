"""
ApexTender v2.0 - FastAPI Backend Application Entrypoint
Lightweight, cost-optimized RAG engine running with <120MB baseline RAM footprint
on Render Free Tier (<512MB RAM cap).
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.routers.system import router as system_router
from app.routers.query import router as query_router
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store
from app.services.llm import get_llm_service

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("apextender.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup resource allocation and graceful shutdown cleanup.
    """
    logger.info(
        f"Starting ApexTender v2.0 Backend Engine [Env: {settings.ENVIRONMENT}] "
        f"[Target RAM Limit: {settings.MEMORY_TARGET_LIMIT_MB}MB]"
    )
    yield
    logger.info("Shutting down ApexTender v2.0 Backend Engine...")
    # Close pooled HTTP clients
    embedding_svc = get_embedding_service()
    await embedding_svc.close()
    vector_svc = get_vector_store()
    await vector_svc.close()
    llm_svc = get_llm_service()
    await llm_svc.close()


def create_app() -> FastAPI:
    """
    FastAPI application factory.
    """
    app = FastAPI(
        title="ApexTender v2.0 RAG Backend",
        description="Production-Grade, Free-Tier-Proof RAG Engine for Enterprise RFP Analysis",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    # Configure Rate Limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure CORS
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    
    # Forcefully allow Vercel origins to prevent CORS blocking
    if "https://rfpanda.vercel.app" not in origins:
        origins.append("https://rfpanda.vercel.app")
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
        
    # W3C CORS spec disallows credentials with wildcard origin
    use_credentials = "*" not in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=use_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Validation Error Handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation failed",
                "details": exc.errors(),
                "body": str(exc.body)
            }
        )

    # Global Unhandled Error Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred."
            }
        )

    # Include Routers
    app.include_router(system_router)
    app.include_router(query_router)

    # Root Endpoint
    @app.get("/", tags=["Root"])
    async def root_index():
        return {
            "name": "ApexTender v2.0 RAG Backend",
            "version": "2.0.0",
            "status": "online",
            "environment": settings.ENVIRONMENT,
            "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled"
        }

    return app


app = create_app()

"""
ApexTender v2.0 - Request and Response Pydantic Models
Defines type-safe data transfer objects for RAG queries, SSE streaming payloads,
citation metadata, memory telemetry, and fallback ingestion.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class QueryRequest(BaseModel):
    """
    RAG Query payload submitted by frontend client.
    """
    query: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="User question or prompt for RFP analysis",
        examples=["What are the SLA penalty terms in Section 4?"]
    )
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of document UUIDs to scope vector search. If null, searches all user documents."
    )
    match_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of relevant chunks to retrieve from pgvector"
    )
    similarity_threshold: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity cutoff for chunk retrieval (0.0 to 1.0)"
    )
    model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Target Groq LLM model: llama-3.3-70b-versatile | llama-3.1-8b-instant"
    )

    model_config = ConfigDict(extra="ignore")


class SourceCitation(BaseModel):
    """
    Individual matched chunk citation metadata.
    """
    chunk_id: str = Field(..., description="Unique chunk UUID")
    document_id: str = Field(..., description="Parent document UUID")
    file_name: str = Field(..., description="Original filename of the document")
    page_number: int = Field(default=1, description="Page number of the chunk in source document")
    section_header: str = Field(default="", description="Section header or title if extracted")
    similarity: float = Field(..., description="Cosine similarity score (0.0 - 1.0)")
    snippet: str = Field(..., description="Excerpt content from chunk")

    model_config = ConfigDict(extra="ignore")


class SourcesMetadata(BaseModel):
    """
    List of source citations emitted in the SSE 'sources' or 'metadata' event.
    """
    sources: List[SourceCitation] = Field(default_factory=list, description="Array of matched document chunks")


class TokenDelta(BaseModel):
    """
    Single streaming token chunk emitted in the SSE 'token' event.
    """
    delta: str = Field(..., description="Incremental text token delta")
    text: Optional[str] = Field(default=None, description="Mirrors delta for cross-client compatibility")


class DoneEvent(BaseModel):
    """
    Completion summary emitted in the SSE 'done' event.
    """
    finish_reason: str = Field(default="stop", description="Reason streaming finished")
    model: Optional[str] = Field(default=None, description="LLM model used")
    total_sources: Optional[int] = Field(default=None, description="Number of citation chunks matched")
    prompt_tokens: Optional[int] = Field(default=None, description="Total prompt tokens consumed")
    completion_tokens: Optional[int] = Field(default=None, description="Total completion tokens generated")
    total_time_ms: Optional[float] = Field(default=None, description="End-to-end latency in milliseconds")


class ErrorEvent(BaseModel):
    """
    Error payload emitted in the SSE 'error' event.
    """
    error: str = Field(..., description="Human-readable error explanation")
    code: str = Field(default="QUERY_ERROR", description="Machine-readable error classification code")


class FallbackParsePage(BaseModel):
    """
    Extracted page text from browser-side PDF.js fallback parser.
    """
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(..., description="Plaintext or markdown extracted from page")


class FallbackParseRequest(BaseModel):
    """
    Payload for browser-side fallback text ingestion.
    """
    document_id: str = Field(..., description="UUID of document to ingest text into")
    pages: Optional[List[FallbackParsePage]] = Field(default=None, description="Structured page-by-page text")
    extracted_text: Optional[str] = Field(default=None, description="Aggregated full document text")
    parser_used: Optional[str] = Field(default="pdfjs_client_fallback", description="Identifier of parser used")


class MemoryMetrics(BaseModel):
    """
    Process memory telemetry ensuring compliance with Render free tier (<300MB target).
    """
    rss_mb: float = Field(..., description="Resident Set Size memory in Megabytes")
    vms_mb: float = Field(..., description="Virtual Memory Size in Megabytes")
    percent: float = Field(..., description="Memory percentage of host system")
    target_limit_mb: float = Field(default=300.0, description="Memory target threshold in MB")
    within_limits: bool = Field(..., description="True if RSS memory is strictly < 300MB")


class HealthResponse(BaseModel):
    """
    System health and liveness probe response.
    """
    status: str = Field(default="healthy", description="System health status: healthy | degraded | unhealthy")
    version: str = Field(default="2.0.0", description="Backend application version")
    environment: str = Field(default="development", description="Current execution environment")
    uptime_seconds: float = Field(..., description="Process uptime in seconds")
    memory: MemoryMetrics = Field(..., description="Live memory diagnostics")


class SystemMetrics(BaseModel):
    """
    Detailed system resource metrics for performance verification.
    """
    memory_rss_mb: float = Field(..., description="Process RSS RAM in MB")
    memory_vms_mb: float = Field(..., description="Process VMS RAM in MB")
    cpu_percent: float = Field(..., description="Process CPU usage percentage")
    threads_count: int = Field(..., description="Active thread count")
    target_limit_mb: float = Field(default=300.0, description="RAM target upper bound")
    within_limits: bool = Field(..., description="Compliance status (<300MB)")
    uptime_seconds: Optional[float] = Field(default=None, description="Uptime in seconds")

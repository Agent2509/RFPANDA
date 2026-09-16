"""
ApexTender v2.0 - Async Voyage AI Embedding Service
Generates 1024-dimensional dense vector embeddings using Voyage AI REST API (voyage-3-lite / voyage-3)
with exponential backoff retries and zero local model weights (<120MB RSS footprint).
"""

import asyncio
import hashlib
import logging
import math
import random
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings

logger = logging.getLogger("apextender.embedding")


class VoyageEmbeddingError(Exception):
    """Exception raised when Voyage AI embedding API fails."""
    pass


class VoyageEmbeddingService:
    """
    Production async client for Voyage AI embeddings API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        self.api_key = api_key or settings.VOYAGE_API_KEY
        self.api_url = api_url or settings.VOYAGE_API_URL
        self.model = model or settings.VOYAGE_MODEL
        self.max_retries = max_retries if max_retries is not None else settings.VOYAGE_MAX_RETRIES
        self.timeout = timeout if timeout is not None else settings.VOYAGE_TIMEOUT_SECONDS
        self._external_client = http_client
        self._internal_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Returns active HTTP client or initializes pooled internal client."""
        if self._external_client is not None:
            return self._external_client
        if self._internal_client is None or self._internal_client.is_closed:
            self._internal_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
            )
        return self._internal_client

    async def close(self):
        """Closes internal HTTP client if initialized."""
        if self._internal_client and not self._internal_client.is_closed:
            await self._internal_client.aclose()
            self._internal_client = None

    def _generate_deterministic_mock_vector(self, text: str, dim: int = 1024) -> List[float]:
        """
        Generates a deterministic L2-normalized 1024d float vector for test mode or mock keys.
        """
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed)
        raw = [rng.gauss(0.0, 1.0) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [round(x / norm, 6) for x in raw]

    async def create_embeddings(
        self,
        texts: List[str],
        input_type: str = "query",
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generates vector embeddings for a list of strings with exponential backoff on 429/5xx.
        
        Args:
            texts: List of text strings to embed.
            input_type: 'query' for user questions, 'document' for knowledge chunks.
            model: Optional model override (default voyage-3-lite).

        Returns:
            List of 1024-dimensional float vector lists.
        """
        if not texts:
            return []

        # If test mode is active or dummy API key is configured (and no custom mock transport is injected)
        if self._external_client is None and (self.api_key.startswith("voyage-mock") or self.api_key == "mock-key"):
            return [self._generate_deterministic_mock_vector(t) for t in texts]

        target_model = model or self.model
        payload = {
            "input": texts,
            "model": target_model,
            "input_type": input_type,
            "output_dimension": 1024
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        client = await self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("data", [])
                    # Sort by index if returned
                    results.sort(key=lambda item: item.get("index", 0))
                    return [item["embedding"] for item in results]

                elif response.status_code == 429 or response.status_code >= 500:
                    retry_after_header = response.headers.get("retry-after")
                    if retry_after_header and retry_after_header.isdigit():
                        delay = float(retry_after_header)
                    else:
                        delay = (0.5 * (2 ** attempt)) + (random.random() * 0.2)
                    
                    logger.warning(
                        f"Voyage AI HTTP {response.status_code}. Retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})."
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise VoyageEmbeddingError(
                            f"Voyage AI rate limit / server error after {self.max_retries} retries: "
                            f"HTTP {response.status_code} - {response.text}"
                        )
                else:
                    raise VoyageEmbeddingError(
                        f"Voyage AI API error HTTP {response.status_code}: {response.text}"
                    )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = exc
                delay = (0.5 * (2 ** attempt)) + (random.random() * 0.2)
                logger.warning(
                    f"Voyage AI network/timeout error: {str(exc)}. Retrying in {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.max_retries})."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise VoyageEmbeddingError(
                        f"Voyage AI network request failed after {self.max_retries} retries: {str(exc)}"
                    ) from exc

        raise VoyageEmbeddingError(f"Voyage AI embedding failed: {str(last_error)}")

    async def embed_query(self, query: str, model: Optional[str] = None) -> List[float]:
        """
        Embeds a single query string using input_type='query'.
        """
        vectors = await self.create_embeddings([query], input_type="query", model=model)
        if not vectors:
            raise VoyageEmbeddingError("Voyage AI returned empty embedding for query.")
        return vectors[0]

    async def embed_documents(
        self,
        texts: List[str],
        batch_size: int = 64,
        model: Optional[str] = None,
        delay_between_batches: float = 0.0
    ) -> List[List[float]]:
        """
        Embeds a large list of document chunks in batches using input_type='document'.
        """
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_vectors = await self.create_embeddings(batch, input_type="document", model=model)
            all_embeddings.extend(batch_vectors)
            if delay_between_batches > 0 and i + batch_size < len(texts):
                import asyncio
                await asyncio.sleep(delay_between_batches)
        return all_embeddings


_embedding_service_instance: Optional[VoyageEmbeddingService] = None


def get_embedding_service() -> VoyageEmbeddingService:
    """Singleton getter for VoyageEmbeddingService."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = VoyageEmbeddingService()
    return _embedding_service_instance

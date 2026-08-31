"""
ApexTender v2.0 - Supabase pgvector Vector Store Client
Executes high-performance cosine similarity vector searches via the `match_documents` RPC
and asynchronously refreshes retention access timestamps via `touch_document_last_queried`.
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings

logger = logging.getLogger("apextender.vector_store")


class VectorStoreError(Exception):
    """Exception raised when Supabase vector search or RPC fails."""
    pass


class SupabaseVectorStore:
    """
    Async Supabase pgvector and PostgREST client.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        timeout: float = 15.0,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        self.supabase_url = (supabase_url or settings.SUPABASE_URL).rstrip("/")
        self.supabase_key = supabase_key or settings.SUPABASE_SERVICE_ROLE_KEY
        self.timeout = timeout
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

    def _get_headers(self) -> Dict[str, str]:
        """Builds standard PostgREST request headers with service role privileges."""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def match_documents(
        self,
        query_embedding: List[float],
        filter_user_id: str,
        filter_document_ids: Optional[List[str]] = None,
        match_threshold: float = 0.25,
        match_count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes the `match_documents` PostgreSQL RPC in Supabase.
        
        Returns a list of matched chunk records sorted by similarity descending:
        [
            {
                "chunk_id": "...",
                "document_id": "...",
                "file_name": "...",
                "page_number": 1,
                "section_header": "...",
                "similarity": 0.88,
                "content": "...",
                "metadata": {...}
            },
            ...
        ]
        """
        rpc_url = f"{self.supabase_url}/rest/v1/rpc/match_documents"
        client = await self._get_client()

        # If multiple document IDs are provided, handle single or multiple
        target_doc_id = filter_document_ids[0] if (filter_document_ids and len(filter_document_ids) == 1) else None

        payload: Dict[str, Any] = {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count,
            "filter_user_id": filter_user_id,
            "filter_document_id": target_doc_id
        }

        try:
            response = await client.post(
                rpc_url,
                json=payload,
                headers=self._get_headers()
            )

            if response.status_code != 200:
                logger.error(f"Supabase RPC match_documents error HTTP {response.status_code}: {response.text}")
                raise VectorStoreError(f"Vector search failed HTTP {response.status_code}: {response.text}")

            raw_results: List[Dict[str, Any]] = response.json()

            # Normalize result dictionary structure
            formatted_chunks: List[Dict[str, Any]] = []
            for item in raw_results:
                chunk_id = item.get("id") or item.get("chunk_id") or ""
                doc_id = item.get("document_id") or ""
                doc_name = item.get("document_name") or item.get("file_name") or "Document"
                meta = item.get("metadata") or {}
                page_num = meta.get("page_number") or item.get("page_number") or 1
                section = meta.get("section_header") or item.get("section_header") or ""
                similarity = float(item.get("similarity", 0.0))
                content = item.get("content", "")

                # If multiple document_ids were passed in request, filter in application layer if RPC only accepts single filter_document_id
                if filter_document_ids and len(filter_document_ids) > 1:
                    if doc_id not in filter_document_ids:
                        continue

                formatted_chunks.append({
                    "chunk_id": str(chunk_id),
                    "document_id": str(doc_id),
                    "file_name": str(doc_name),
                    "page_number": int(page_num),
                    "section_header": str(section),
                    "similarity": round(similarity, 4),
                    "content": str(content),
                    "metadata": meta
                })

            return formatted_chunks

        except httpx.RequestError as exc:
            logger.error(f"Supabase vector store connection error: {str(exc)}")
            raise VectorStoreError(f"Supabase network connection error: {str(exc)}") from exc

    async def touch_document_last_queried(self, document_ids: List[str]) -> int:
        """
        Executes `touch_document_last_queried` RPC to refresh `last_queried_at` timestamp.
        """
        if not document_ids:
            return 0

        rpc_url = f"{self.supabase_url}/rest/v1/rpc/touch_document_last_queried"
        client = await self._get_client()

        payload = {"p_document_ids": document_ids}

        try:
            response = await client.post(
                rpc_url,
                json=payload,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                return int(result) if isinstance(result, (int, float)) else len(document_ids)
            else:
                logger.warning(
                    f"touch_document_last_queried returned HTTP {response.status_code}: {response.text}"
                )
                return 0
        except Exception as exc:
            logger.warning(f"Failed to touch document timestamps: {str(exc)}")
            return 0

    async def increment_query_count(self, user_id: str) -> None:
        """Executes increment_query_count RPC. Raises an exception if limit exceeded."""
        rpc_url = f"{self.supabase_url}/rest/v1/rpc/increment_query_count"
        client = await self._get_client()
        payload = {"p_user_id": user_id}
        try:
            response = await client.post(rpc_url, json=payload, headers=self._get_headers())
            if response.status_code != 200:
                err_text = response.text
                if "Free tier limit reached" in err_text:
                    raise VectorStoreError("Free tier limit reached: You can only ask up to 50 questions.")
                logger.error(f"increment_query_count HTTP {response.status_code}: {err_text}")
                raise VectorStoreError(f"Usage tracking failed HTTP {response.status_code}")
        except httpx.RequestError as exc:
            logger.error(f"increment_query_count connection error: {str(exc)}")
            raise VectorStoreError("Usage tracking network error.") from exc

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all documents owned by user_id from Supabase REST endpoint.
        """
        url = f"{self.supabase_url}/rest/v1/documents?user_id=eq.{user_id}&select=*&order=created_at.desc"
        client = await self._get_client()

        try:
            response = await client.get(url, headers=self._get_headers())
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch documents: HTTP {response.status_code} - {response.text}")
                return []
        except Exception as exc:
            logger.error(f"Error fetching user documents: {str(exc)}")
            return []


_vector_store_instance: Optional[SupabaseVectorStore] = None


def get_vector_store() -> SupabaseVectorStore:
    """Singleton getter for SupabaseVectorStore."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = SupabaseVectorStore()
    return _vector_store_instance

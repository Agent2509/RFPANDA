"""
ApexTender v2.0 Opaque-Box Test Client.
Provides a clean, high-level asynchronous API to interact with all ApexTender subsystems,
parse SSE streams, and verify interface contracts.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
import httpx

class ApexTenderTestClient:
    def __init__(self, base_url: str = "http://testserver", app=None):
        self.base_url = base_url
        self.app = app
        if app is not None:
            transport = httpx.ASGITransport(app=app)
            self.http_client = httpx.AsyncClient(transport=transport, base_url=base_url, timeout=30.0)
        else:
            self.http_client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def close(self):
        await self.http_client.aclose()

    # ==========================================
    # Health & System Metrics
    # ==========================================
    async def get_health(self) -> httpx.Response:
        return await self.http_client.get("/health")

    async def get_system_metrics(self) -> httpx.Response:
        return await self.http_client.get("/api/system/metrics")

    # ==========================================
    # Direct Storage Upload
    # ==========================================
    async def upload_file_to_storage(
        self,
        bucket_id: str,
        path: str,
        file_bytes: bytes,
        mime_type: str,
        token: str
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": mime_type
        }
        return await self.http_client.post(
            f"/storage/v1/object/{bucket_id}/{path}",
            content=file_bytes,
            headers=headers
        )

    # ==========================================
    # Edge Function Ingestion
    # ==========================================
    async def trigger_process_document(
        self,
        document_id: str,
        token: str,
        storage_path: Optional[str] = None
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"document_id": document_id}
        if storage_path:
            payload["storage_path"] = storage_path
        return await self.http_client.post(
            "/functions/v1/process-document",
            json=payload,
            headers=headers
        )

    # ==========================================
    # Fallback Parsing Ingestion
    # ==========================================
    async def trigger_fallback_ingest(
        self,
        document_id: str,
        token: str,
        extracted_text: Optional[str] = None,
        pages: Optional[List[Dict[str, Any]]] = None,
        parser_used: str = "pdfjs_client_fallback"
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "document_id": document_id,
            "parser_used": parser_used
        }
        if extracted_text is not None:
            payload["extracted_text"] = extracted_text
        if pages is not None:
            payload["pages"] = pages
        return await self.http_client.post(
            "/functions/v1/ingest-fallback-text",
            json=payload,
            headers=headers
        )

    # ==========================================
    # Documents Library & keep_forever
    # ==========================================
    async def list_documents(self, token: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        return await self.http_client.get("/api/documents", headers=headers)

    async def toggle_keep_forever(
        self,
        document_id: str,
        keep_forever: bool,
        token: str
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        return await self.http_client.patch(
            f"/api/documents/{document_id}/keep-forever",
            json={"keep_forever": keep_forever},
            headers=headers
        )

    # ==========================================
    # RAG Query & SSE Stream Consumer
    # ==========================================
    async def query_stream(
        self,
        query: str,
        token: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.25,
        match_count: int = 5,
        model: str = "llama-3.3-70b-versatile"
    ) -> Tuple[int, List[Dict[str, Any]], str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Executes POST /api/query and consumes the Server-Sent Events stream.
        Returns: (status_code, sources_list, full_streaming_text, done_data, error_data)
        """
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "query": query,
            "document_ids": document_ids,
            "similarity_threshold": similarity_threshold,
            "match_count": match_count,
            "model": model
        }

        response = await self.http_client.post(
            "/api/query",
            json=payload,
            headers=headers
        )

        if response.status_code != 200:
            return response.status_code, [], "", None, {"error": response.text}

        # Parse SSE stream
        raw_text = response.text
        lines = raw_text.split("\n\n")

        sources = []
        streamed_tokens = []
        done_payload = None
        error_payload = None

        for block in lines:
            trimmed = block.strip()
            if not trimmed:
                continue

            event_type = None
            data_str = None

            for line in trimmed.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    data_str = line[6:].strip()

            if not data_str:
                continue

            try:
                data_json = json.loads(data_str)
            except Exception:
                continue

            if event_type == "sources":
                sources = data_json.get("sources", [])
            elif event_type == "token":
                streamed_tokens.append(data_json.get("delta", data_json.get("text", "")))
            elif event_type == "done":
                done_payload = data_json
            elif event_type == "error":
                error_payload = data_json

        full_text = "".join(streamed_tokens)
        return response.status_code, sources, full_text, done_payload, error_payload

    # ==========================================
    # Auto-Cleanup RPC
    # ==========================================
    async def trigger_cleanup_cron(
        self,
        days: int = 30,
        simulated_now_iso: Optional[str] = None
    ) -> httpx.Response:
        params = {"days": days}
        if simulated_now_iso:
            params["simulated_now_iso"] = simulated_now_iso
        return await self.http_client.post(
            "/rest/v1/rpc/cleanup_stale_documents",
            params=params
        )

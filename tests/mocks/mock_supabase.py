"""
Mock Supabase Backend (Auth, Storage, PostgreSQL pgvector, and RPCs)
for ApexTender v2.0 E2E Testing.
Opaque-box emulator verifying database schemas, RLS policies, vector similarity, and pg_cron cleanup.
"""

import math
import time
import datetime
import uuid
import jwt
from typing import Dict, Any, List, Optional, Tuple

JWT_SECRET = "super-secret-supabase-jwt-key-for-testing-only-12345"

class MockSupabaseService:
    def __init__(self, jwt_secret: str = JWT_SECRET):
        self.jwt_secret = jwt_secret
        
        # Auth users: {user_id: {"email": email, "password": password, "role": role}}
        self.users: Dict[str, Dict[str, Any]] = {}
        
        # Storage: {bucket_id: {path: {"data": bytes, "size": int, "mime_type": str, "user_id": str}}}
        self.storage: Dict[str, Dict[str, Dict[str, Any]]] = {
            "rfp-documents": {}
        }
        self.bucket_config = {
            "rfp-documents": {
                "public": False,
                "file_size_limit": 26214400,  # 25 MB
                "allowed_mime_types": [
                    "application/pdf",
                    "text/plain",
                    "text/markdown",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword"
                ]
            }
        }
        
        # Database Tables
        # public.documents: {doc_id: {...}}
        self.documents: Dict[str, Dict[str, Any]] = {}
        
        # public.document_chunks: {chunk_id: {...}}
        self.document_chunks: Dict[str, Dict[str, Any]] = {}
        
        # public.cleanup_audit_logs: [{...}]
        self.cleanup_audit_logs: List[Dict[str, Any]] = []

    # ==========================================
    # Auth Methods
    # ==========================================
    def create_user(self, email: str, password: str = "Password123!", role: str = "authenticated") -> str:
        user_id = str(uuid.uuid4())
        self.users[user_id] = {
            "id": user_id,
            "email": email,
            "password": password,
            "role": role,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        return user_id

    def generate_token(
        self,
        user_id: str,
        email: Optional[str] = None,
        role: str = "authenticated",
        audience: str = "authenticated",
        expires_in_seconds: int = 3600,
        custom_secret: Optional[str] = None,
        missing_sub: bool = False
    ) -> str:
        secret = custom_secret if custom_secret is not None else self.jwt_secret
        now = int(time.time())
        payload = {
            "aud": audience,
            "role": role,
            "iat": now,
            "exp": now + expires_in_seconds,
            "email": email or (self.users.get(user_id, {}).get("email", "test@apextender.com"))
        }
        if not missing_sub:
            payload["sub"] = user_id
            
        return jwt.encode(payload, secret, algorithm="HS256")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Validates Supabase JWT signature and claims.
        """
        payload = jwt.decode(
            token,
            self.jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True, "verify_aud": True}
        )
        if "sub" not in payload or not payload["sub"]:
            raise jwt.PyJWTError("Missing subject (sub) claim")
        return payload

    # ==========================================
    # Storage Methods & RLS
    # ==========================================
    def storage_upload(
        self,
        bucket_id: str,
        path: str,
        data: bytes,
        mime_type: str,
        user_id: str
    ) -> Dict[str, Any]:
        bucket = self.bucket_config.get(bucket_id)
        if not bucket:
            return {"status_code": 404, "error": f"Bucket '{bucket_id}' not found"}

        # RLS check: path must start with user_id/
        path_parts = path.strip("/").split("/")
        if not path_parts or path_parts[0] != user_id:
            return {"status_code": 403, "error": "Storage RLS violation: cannot upload to another tenant directory"}

        # Size check
        if len(data) > bucket["file_size_limit"]:
            return {"status_code": 413, "error": f"Payload too large: exceeds {bucket['file_size_limit']} bytes"}

        # MIME type check
        if bucket["allowed_mime_types"] and mime_type not in bucket["allowed_mime_types"]:
            return {"status_code": 415, "error": f"Unsupported MIME type '{mime_type}'"}

        self.storage[bucket_id][path] = {
            "data": data,
            "size": len(data),
            "mime_type": mime_type,
            "user_id": user_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        return {"status_code": 200, "path": path, "size": len(data)}

    def storage_download(self, bucket_id: str, path: str, user_id: str) -> Tuple[int, Optional[bytes], Optional[str]]:
        path_parts = path.strip("/").split("/")
        if not path_parts or path_parts[0] != user_id:
            return 403, None, "Storage RLS violation"
        obj = self.storage.get(bucket_id, {}).get(path)
        if not obj:
            return 404, None, "File not found"
        return 200, obj["data"], None

    def storage_delete(self, bucket_id: str, path: str, user_id: str) -> Tuple[int, Optional[str]]:
        path_parts = path.strip("/").split("/")
        if not path_parts or path_parts[0] != user_id:
            return 403, "Storage RLS violation"
        if path in self.storage.get(bucket_id, {}):
            del self.storage[bucket_id][path]
            return 200, None
        return 404, "File not found"

    # ==========================================
    # Database CRUD & RPC Stored Procedures
    # ==========================================
    def insert_document(
        self,
        doc_id: str,
        user_id: str,
        name: str,
        storage_path: str,
        file_size: int,
        mime_type: str = "application/pdf",
        keep_forever: bool = False,
        status: str = "uploaded",
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime.datetime] = None,
        last_queried_at: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc)
        doc = {
            "id": doc_id,
            "user_id": user_id,
            "name": name,
            "filename": name,
            "storage_path": storage_path,
            "file_path": storage_path,
            "file_size": file_size,
            "file_size_bytes": file_size,
            "mime_type": mime_type,
            "status": status,
            "error_message": None,
            "keep_forever": keep_forever,
            "last_queried_at": (last_queried_at or now).isoformat(),
            "created_at": (created_at or now).isoformat(),
            "updated_at": (created_at or now).isoformat(),
            "metadata": metadata or {},
            "total_chunks": 0
        }
        self.documents[doc_id] = doc
        return doc

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        doc.update(updates)
        doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return doc

    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        count = 0
        for c in chunks:
            chunk_id = c.get("id") or str(uuid.uuid4())
            self.document_chunks[chunk_id] = {
                "id": chunk_id,
                "document_id": c["document_id"],
                "user_id": c["user_id"],
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "embedding": c.get("embedding", []),
                "token_count": c.get("token_count", max(1, len(c["content"]) // 4)),
                "metadata": c.get("metadata", {}),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            count += 1
            
        # Update total_chunks on document
        if chunks:
            doc_id = chunks[0]["document_id"]
            if doc_id in self.documents:
                self.documents[doc_id]["total_chunks"] = len([
                    ch for ch in self.document_chunks.values() if ch["document_id"] == doc_id
                ])
        return count

    # ==========================================
    # RPC: match_documents
    # ==========================================
    def match_documents(
        self,
        query_embedding: List[float],
        match_threshold: float = 0.2,
        match_count: int = 5,
        filter_user_id: Optional[str] = None,
        filter_document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Cosine Similarity match against document_chunks:
        similarity = 1 - (embedding <=> query_embedding) = dot(a, b) / (norm(a)*norm(b))
        """
        if not filter_user_id:
            raise ValueError("Access denied: filter_user_id is required.")

        def cosine_similarity(v1: List[float], v2: List[float]) -> float:
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

        results = []
        for chunk in self.document_chunks.values():
            # Tenant isolation
            if chunk["user_id"] != filter_user_id:
                continue

            # Document ID filtering
            if filter_document_ids and chunk["document_id"] not in filter_document_ids:
                continue

            emb = chunk.get("embedding", [])
            sim = cosine_similarity(query_embedding, emb)
            
            if sim >= match_threshold:
                doc = self.documents.get(chunk["document_id"], {})
                results.append({
                    "chunk_id": chunk["id"],
                    "id": chunk["id"],
                    "document_id": chunk["document_id"],
                    "document_name": doc.get("name", "Document.pdf"),
                    "file_name": doc.get("name", "Document.pdf"),
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "similarity": round(sim, 4),
                    "metadata": chunk.get("metadata", {}),
                    "token_count": chunk.get("token_count", 0),
                    "page_number": chunk.get("metadata", {}).get("page_number", 1),
                    "section_header": chunk.get("metadata", {}).get("section_header", "General")
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:match_count]

    # ==========================================
    # RPC: touch_document_last_queried
    # ==========================================
    def touch_document_last_queried(self, p_document_ids: List[str]) -> int:
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        count = 0
        for doc_id in p_document_ids:
            if doc_id in self.documents:
                self.documents[doc_id]["last_queried_at"] = now_str
                self.documents[doc_id]["updated_at"] = now_str
                count += 1
        return count

    # ==========================================
    # RPC: cleanup_stale_documents
    # ==========================================
    def cleanup_stale_documents(
        self,
        retention_interval: datetime.timedelta = datetime.timedelta(days=30),
        simulated_now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        """
        Deletes documents where keep_forever == False and last_queried_at/created_at < now - retention_interval.
        Cascades to chunks and removes storage files. Logs to cleanup_audit_logs.
        """
        now = simulated_now or datetime.datetime.now(datetime.timezone.utc)
        cutoff_time = now - retention_interval

        stale_doc_ids = []
        stale_storage_paths = []
        freed_bytes = 0

        for doc_id, doc in list(self.documents.items()):
            if doc.get("keep_forever", False) is True:
                continue

            last_activity_str = doc.get("last_queried_at") or doc.get("created_at")
            if not last_activity_str:
                continue

            last_activity = datetime.datetime.fromisoformat(last_activity_str)
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=datetime.timezone.utc)

            if last_activity < cutoff_time:
                stale_doc_ids.append(doc_id)
                stale_storage_paths.append(doc.get("storage_path") or doc.get("file_path"))
                freed_bytes += doc.get("file_size", 0)

        if not stale_doc_ids:
            return {
                "status": "no_op",
                "message": "No stale documents found exceeding retention window.",
                "cutoff_time": cutoff_time.isoformat(),
                "deleted_documents_count": 0,
                "deleted_chunks_count": 0,
                "freed_bytes": 0
            }

        # Count chunks to delete
        deleted_chunks_count = 0
        for chunk_id, chunk in list(self.document_chunks.items()):
            if chunk["document_id"] in stale_doc_ids:
                del self.document_chunks[chunk_id]
                deleted_chunks_count += 1

        # Delete from storage
        for path in stale_storage_paths:
            if path and path in self.storage.get("rfp-documents", {}):
                del self.storage["rfp-documents"][path]

        # Delete from documents
        for doc_id in stale_doc_ids:
            del self.documents[doc_id]

        deleted_docs_count = len(stale_doc_ids)

        audit_entry = {
            "id": str(uuid.uuid4()),
            "deleted_documents_count": deleted_docs_count,
            "deleted_chunks_count": deleted_chunks_count,
            "freed_bytes_estimate": freed_bytes,
            "executed_at": now.isoformat(),
            "details": {
                "retention_interval": str(retention_interval),
                "cutoff_time": cutoff_time.isoformat(),
                "deleted_doc_ids": stale_doc_ids,
                "deleted_storage_paths": stale_storage_paths
            }
        }
        self.cleanup_audit_logs.append(audit_entry)

        return {
            "status": "success",
            "deleted_documents_count": deleted_docs_count,
            "deleted_chunks_count": deleted_chunks_count,
            "freed_bytes": freed_bytes,
            "cutoff_time": cutoff_time.isoformat(),
            "executed_at": now.isoformat()
        }

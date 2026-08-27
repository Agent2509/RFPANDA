"""
Mock Voyage AI Service for ApexTender v2.0 E2E Testing.
Emulates Voyage AI 1024-dimensional embedding generation (voyage-3 / voyage-3-lite).
Deterministic, normalized vector embeddings with controllable rate limits and latency.
"""

import math
import hashlib
import re
from typing import List, Dict, Any, Optional

class MockVoyageService:
    def __init__(self, dimension: int = 1024, default_model: str = "voyage-3-lite"):
        self.dimension = dimension
        self.default_model = default_model
        self.rate_limit_enabled = False
        self.rate_limit_threshold = 10
        self.request_count = 0
        self.total_tokens_processed = 0

    def set_rate_limit(self, enabled: bool = True, threshold: int = 10):
        self.rate_limit_enabled = enabled
        self.rate_limit_threshold = threshold
        self.request_count = 0

    def reset_stats(self):
        self.request_count = 0
        self.total_tokens_processed = 0

    def _generate_deterministic_vector(self, text: str, input_type: str = "document") -> List[float]:
        """
        Generates a 1024-dimensional normalized float vector from text content.
        Uses shared semantic projection so matching queries and documents produce realistic
        high cosine similarities (0.6 - 0.9) while dissimilar content produces low scores (<0.2).
        """
        clean_text = text.strip().lower()
        words = [w for w in re.findall(r'[a-zA-Z0-9]+', clean_text) if len(w) > 2]
        
        vector = [0.0] * self.dimension
        
        # Word-level n-gram feature hashing to simulate dense subword embeddings
        for word in words:
            # 16 hash projections per word
            h = hashlib.sha256(word.encode("utf-8")).digest()
            for k in range(16):
                idx = (h[k * 2] * 256 + h[k * 2 + 1]) % self.dimension
                sign = 1.0 if h[(k * 2) % len(h)] % 2 == 0 else -1.0
                vector[idx] += 3.0 * sign

        # Global base noise
        hasher = hashlib.md5(clean_text.encode("utf-8"))
        seed_bytes = hasher.digest()
        for i in range(self.dimension):
            byte_val = seed_bytes[i % len(seed_bytes)]
            vector[i] += (float(byte_val) / 255.0) * 0.1 - 0.05

        # Normalize vector to unit length (L2 norm)
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

    def create_embeddings(
        self,
        inputs: List[str],
        model: Optional[str] = None,
        input_type: str = "document",
        output_dimension: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Emulates POST /v1/embeddings
        """
        self.request_count += 1
        
        if self.rate_limit_enabled and self.request_count > self.rate_limit_threshold:
            raise RateLimitException("Voyage AI Rate Limit Exceeded: 429 Too Many Requests")
        
        model_name = model or self.default_model
        dim = output_dimension or self.dimension
        
        embeddings_data = []
        total_tokens = 0
        
        for idx, text in enumerate(inputs):
            token_est = max(1, len(text) // 4)
            total_tokens += token_est
            vec = self._generate_deterministic_vector(text, input_type=input_type)
            if len(vec) != dim:
                vec = vec[:dim]
            embeddings_data.append({
                "object": "embedding",
                "embedding": vec,
                "index": idx
            })
        
        self.total_tokens_processed += total_tokens
        
        return {
            "object": "list",
            "data": embeddings_data,
            "model": model_name,
            "usage": {
                "total_tokens": total_tokens
            }
        }


class RateLimitException(Exception):
    pass

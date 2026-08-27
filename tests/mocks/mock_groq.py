"""
Mock Groq AI Service for ApexTender v2.0 E2E Testing.
Emulates Groq Cloud Llama 3 (llama-3.3-70b-versatile, llama-3.1-8b-instant) SSE token streaming.
Emits Server-Sent Events (SSE) in standard OpenAI / Groq format.
"""

import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional

class MockGroqService:
    def __init__(self, default_model: str = "llama-3.3-70b-versatile"):
        self.default_model = default_model
        self.simulate_error = False
        self.error_type = "500"
        self.stream_delay = 0.001  # Small delay for non-blocking stream simulation

    def set_error_simulation(self, enabled: bool = True, error_type: str = "500"):
        self.simulate_error = enabled
        self.error_type = error_type

    def _synthesize_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Synthesizes a realistic, grounded RFP answer incorporating the matched context chunks
        and inline citation markers.
        """
        if not context_chunks:
            return (
                "Based on the provided documents, I could not find sufficient information to answer your query. "
                "Please verify that the relevant RFP documents are uploaded and selected."
            )

        citations = []
        snippets = []
        for i, chunk in enumerate(context_chunks):
            doc_name = chunk.get("document_name") or chunk.get("file_name") or "RFP_Document.pdf"
            page = chunk.get("metadata", {}).get("page_number") or chunk.get("page_number") or (i + 1)
            section = chunk.get("metadata", {}).get("section_header") or chunk.get("section_header") or f"Section {i+1}"
            citations.append(f"[[Doc: {doc_name}, p. {page} - {section}]]")
            content = chunk.get("content", "")
            snippets.append(content[:150] + "...")

        answer_lines = [
            f"Based on the analysis of the RFP documentation, here are the key findings regarding: '{query}':\n\n",
            f"1. **Core Requirements & SLA Specifications**:\n",
            f"   - {snippets[0] if len(snippets) > 0 else 'The contractor must adhere to the defined service levels.'} {citations[0] if len(citations) > 0 else ''}\n\n",
        ]
        
        if len(snippets) > 1:
            answer_lines.append(
                f"2. **Compliance & Pricing Details**:\n"
                f"   - {snippets[1]} {citations[1]}\n\n"
            )
            
        answer_lines.append(
            "In summary, all mandatory compliance criteria must be validated prior to proposal submission."
        )
        return "".join(answer_lines)

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        context_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Yields raw Server-Sent Event (SSE) chunks.
        """
        if self.simulate_error:
            if self.error_type == "429":
                raise GroqRateLimitException("Groq API Rate Limit: 429 Too Many Requests")
            elif self.error_type == "auth":
                raise GroqAuthException("Invalid Groq API Key: 401 Unauthorized")
            else:
                raise GroqServerException("Groq API Internal Error: 500 Internal Server Error")

        model_name = model or self.default_model
        
        # Extract query from messages
        user_query = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_query = msg.get("content", "")
                
        full_answer = self._synthesize_answer(user_query, context_chunks or [])
        
        # Split into tokens/words for realistic streaming
        words = full_answer.split(" ")
        
        for i, word in enumerate(words):
            token_delta = word + (" " if i < len(words) - 1 else "")
            chunk_payload = {
                "id": f"chatcmpl-mock-{i}",
                "object": "chat.completion.chunk",
                "created": 1724760000,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": token_delta},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_payload)}\n\n"
            if self.stream_delay > 0:
                await asyncio.sleep(self.stream_delay)

        # Final completion chunk
        final_payload = {
            "id": f"chatcmpl-mock-final",
            "object": "chat.completion.chunk",
            "created": 1724760000,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": max(50, len(user_query) // 4 + sum(len(c.get('content', '')) // 4 for c in (context_chunks or []))),
                "completion_tokens": len(words),
                "total_tokens": max(50, len(user_query) // 4) + len(words)
            }
        }
        yield f"data: {json.dumps(final_payload)}\n\n"
        yield "data: [DONE]\n\n"


class GroqRateLimitException(Exception):
    pass

class GroqAuthException(Exception):
    pass

class GroqServerException(Exception):
    pass

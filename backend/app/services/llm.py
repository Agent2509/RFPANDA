"""
RFPANDA - Groq LLM Async Streaming Service
Orchestrates Llama-3.3-70b-versatile and Llama-3.1-8b-instant via Groq API
with structured RFP system prompts, zero-hallucination guardrails, and real-time token streaming.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from groq import AsyncGroq

from app.config import settings

logger = logging.getLogger("rfpanda.llm")


RFP_SYSTEM_PROMPT = """You are the Senior RFP & Procurement Intelligence Assistant for RFPANDA.

Your objective is to provide high-precision, executive-ready analysis and answers to RFP questions based STRICTLY and EXCLUSIVELY on the provided context excerpts.

*** ZERO HALLUCINATION POLICY ***
You are in ULTRA-STRICT mode. You must NEVER guess, hallucinate, or use outside knowledge to answer the user's question. If the provided context does not contain the answer, you must reply EXACTLY with: "Information not found in the provided documents."

### MANDATORY INSTRUCTIONS:
1. **Strict Grounding**: Base all statements, figures, criteria, deadlines, and technical specifications directly on the provided document chunks. Do NOT assume, extrapolate, or hallucinate facts not present in the text.
2. **Explicit Citations**: When stating facts or requirements from a document, cite the source using the format: `[[Doc: <file_name>, p. <page_number> - <section_header>]]`.
3. **Structured Clarity**: Use clean Markdown formatting, bullet points, headers, and comparison tables for readability.
4. **Missing Information Handling**: If the provided excerpts do not contain enough information to fully answer the question, state clearly: "Based on the provided RFP documents, specific details regarding [topic] were not found."
"""


class LLMServiceError(Exception):
    """Exception raised when Groq streaming fails."""
    pass


class GroqLLMService:
    """
    Async streaming service for Groq Cloud LLM completions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.default_model = default_model or settings.GROQ_MODEL
        self.timeout = timeout or settings.GROQ_TIMEOUT_SECONDS
        self._client: Optional[AsyncGroq] = None

    def _get_client(self) -> AsyncGroq:
        """Returns initialized AsyncGroq client."""
        if self._client is None:
            self._client = AsyncGroq(
                api_key=self.api_key if not self.api_key.startswith("groq-mock") else "gsk_dummy",
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        """Closes the AsyncGroq client if initialized."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    def format_context_prompt(self, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved context chunks into a structured Markdown prompt block.
        """
        if not context_chunks:
            return "No relevant RFP document excerpts found."

        context_blocks = []
        for i, chunk in enumerate(context_chunks, 1):
            file_name = chunk.get("file_name", "Document")
            page_num = chunk.get("page_number", 1)
            section = chunk.get("section_header", "General")
            content = chunk.get("content", "").strip()
            score = chunk.get("similarity", 0.0)

            block = (
                f"### Document Excerpt [{i}]: {file_name} (Page {page_num} | Section: {section} | Score: {score:.2f})\n"
                f"{content}\n"
            )
            context_blocks.append(block)

        return "\n".join(context_blocks)

    async def _mock_stream(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        model: str
    ) -> AsyncGenerator[str, None]:
        """
        Yields realistic mock token deltas for tests and offline development.
        """
        top_chunk = context_chunks[0] if context_chunks else {}
        file_name = top_chunk.get("file_name", "RFP_Specification.pdf")
        page_num = top_chunk.get("page_number", 1)
        section = top_chunk.get("section_header", "Requirements")

        sample_tokens = [
            "Based", " on", " the", " provided", " RFP", " documentation", " in",
            f" **{file_name}**", f" (p. {page_num} - {section})", ":\n\n",
            "1. **Core Requirements**: The vendor must ensure strict compliance with all specified technical and operational criteria.\n",
            f"2. **Evidence**: {top_chunk.get('content', '')[:120]}...\n\n",
            f"[[Doc: {file_name}, p. {page_num} - {section}]]\n"
        ]

        for token in sample_tokens:
            await asyncio.sleep(0.01)
            yield token

    async def stream_chat_completion(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        model: Optional[str] = None,
        custom_system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously streams Groq chat completion tokens for the RAG query.
        
        Yields:
            str: Each incremental text token delta.
        """
        target_model = model or self.default_model

        # Fallback to deterministic mock stream if in TEST_MODE or dummy key
        if settings.TEST_MODE or self.api_key.startswith("groq-mock") or self.api_key == "mock-key":
            async for token in self._mock_stream(query, context_chunks, target_model):
                yield token
            return

        system_instruction = custom_system_prompt or RFP_SYSTEM_PROMPT
        context_str = self.format_context_prompt(context_chunks)

        user_content = (
            f"### CONTEXT EXCERPTS FROM RETRIEVED RFP DOCUMENTS:\n"
            f"{context_str}\n\n"
            f"### USER QUESTION:\n"
            f"{query}\n\n"
            f"Provide a direct, comprehensive, grounded answer with inline citations."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

        client = self._get_client()

        try:
            stream = await client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content

        except Exception as exc:
            logger.error(f"Groq streaming error on model {target_model}: {str(exc)}")
            raise LLMServiceError(f"Groq LLM streaming error: {str(exc)}") from exc


_llm_service_instance: Optional[GroqLLMService] = None


def get_llm_service() -> GroqLLMService:
    """Singleton getter for GroqLLMService."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = GroqLLMService()
    return _llm_service_instance

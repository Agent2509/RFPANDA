"""
ApexTender v2.1 - Lightweight Semantic Chunker (Python)
Port of the TypeScript SemanticChunker used in Supabase Edge Functions.
Splits markdown text into overlapping chunks with ~600 token targets.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("apextender.chunker")


@dataclass
class ChunkResult:
    """A single text chunk with metadata."""
    chunk_index: int
    content: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """
    Markdown-aware semantic chunker that splits text into overlapping chunks.
    Respects markdown headers and paragraph boundaries before falling back
    to sentence-level splitting.
    """

    def __init__(
        self,
        target_tokens: int = 600,
        overlap_tokens: int = 100,
        max_tokens: int = 1000,
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token count using whitespace splitting (~1.3 words per token)."""
        return max(1, int(len(text.split()) / 1.3)) if text.strip() else 0

    def _split_into_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Split markdown text into sections based on headers (# ## ### etc).
        Each section includes its header and body content.
        """
        # Split on markdown headers
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        sections: List[Dict[str, Any]] = []
        last_end = 0
        last_header = ""

        for match in header_pattern.finditer(text):
            # Capture content before this header
            if match.start() > last_end:
                content = text[last_end:match.start()].strip()
                if content:
                    sections.append({
                        "header": last_header,
                        "content": content,
                    })

            last_header = match.group(2).strip()
            last_end = match.end()

        # Capture remaining content after last header
        remaining = text[last_end:].strip()
        if remaining:
            sections.append({
                "header": last_header,
                "content": remaining,
            })

        # If no headers found, treat entire text as one section
        if not sections:
            sections.append({
                "header": "",
                "content": text.strip(),
            })

        return sections

    def _split_section_into_paragraphs(self, text: str) -> List[str]:
        """Split a section into paragraphs on double newlines."""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences on sentence-ending punctuation."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str) -> List[ChunkResult]:
        """
        Chunk text into overlapping segments of ~target_tokens.
        Returns a list of ChunkResult objects.
        """
        if not text or not text.strip():
            return []

        sections = self._split_into_sections(text)
        chunks: List[ChunkResult] = []
        current_content: List[str] = []
        current_tokens = 0
        current_header = ""
        chunk_index = 0

        for section in sections:
            header = section["header"]
            paragraphs = self._split_section_into_paragraphs(section["content"])

            for para in paragraphs:
                para_tokens = self._estimate_tokens(para)

                # If adding this paragraph exceeds max_tokens, flush current chunk
                if current_tokens + para_tokens > self.max_tokens and current_content:
                    chunk_text = "\n\n".join(current_content)
                    chunks.append(ChunkResult(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        token_count=self._estimate_tokens(chunk_text),
                        metadata={
                            "section_header": current_header or header,
                        },
                    ))
                    chunk_index += 1

                    # Create overlap from the tail of the current chunk
                    overlap_text = ""
                    overlap_tokens_count = 0
                    for piece in reversed(current_content):
                        piece_tokens = self._estimate_tokens(piece)
                        if overlap_tokens_count + piece_tokens > self.overlap_tokens:
                            break
                        overlap_text = piece + "\n\n" + overlap_text if overlap_text else piece
                        overlap_tokens_count += piece_tokens

                    current_content = [overlap_text] if overlap_text else []
                    current_tokens = overlap_tokens_count

                # If a single paragraph exceeds max_tokens, split by sentences
                if para_tokens > self.max_tokens:
                    sentences = self._split_into_sentences(para)
                    for sentence in sentences:
                        sent_tokens = self._estimate_tokens(sentence)
                        if current_tokens + sent_tokens > self.target_tokens and current_content:
                            chunk_text = "\n\n".join(current_content)
                            chunks.append(ChunkResult(
                                chunk_index=chunk_index,
                                content=chunk_text,
                                token_count=self._estimate_tokens(chunk_text),
                                metadata={
                                    "section_header": current_header or header,
                                },
                            ))
                            chunk_index += 1
                            current_content = []
                            current_tokens = 0

                        current_content.append(sentence)
                        current_tokens += sent_tokens
                else:
                    current_content.append(para)
                    current_tokens += para_tokens

                # Flush if we've reached the target
                if current_tokens >= self.target_tokens and current_content:
                    chunk_text = "\n\n".join(current_content)
                    chunks.append(ChunkResult(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        token_count=self._estimate_tokens(chunk_text),
                        metadata={
                            "section_header": current_header or header,
                        },
                    ))
                    chunk_index += 1

                    # Overlap
                    overlap_text = ""
                    overlap_tokens_count = 0
                    for piece in reversed(current_content):
                        piece_tokens = self._estimate_tokens(piece)
                        if overlap_tokens_count + piece_tokens > self.overlap_tokens:
                            break
                        overlap_text = piece + "\n\n" + overlap_text if overlap_text else piece
                        overlap_tokens_count += piece_tokens

                    current_content = [overlap_text] if overlap_text else []
                    current_tokens = overlap_tokens_count

            current_header = header

        # Flush remaining content
        if current_content:
            chunk_text = "\n\n".join(current_content)
            final_tokens = self._estimate_tokens(chunk_text)
            if final_tokens > 0:
                chunks.append(ChunkResult(
                    chunk_index=chunk_index,
                    content=chunk_text,
                    token_count=final_tokens,
                    metadata={
                        "section_header": current_header,
                    },
                ))

        logger.info(f"Chunked text into {len(chunks)} chunks (target={self.target_tokens} tokens)")
        return chunks

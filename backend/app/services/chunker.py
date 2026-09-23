"""
ApexTender v2.1 - Lightweight Semantic Chunker (Python)
Port of the TypeScript SemanticChunker used in Supabase Edge Functions.
Splits markdown text into overlapping chunks with ~600 token targets.
Preserves page numbers and markdown tables.
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
    Respects markdown headers, page markers, tables, and paragraph boundaries
    before falling back to sentence-level splitting.
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

    @staticmethod
    def _is_table_block(text: str) -> bool:
        """Determines if a block is a markdown table."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) < 2:
            return False
        table_lines = [l for l in lines if l.startswith("|") and l.count("|") >= 2]
        return len(table_lines) >= 2 and len(table_lines) >= len(lines) * 0.7

    def _split_into_page_segments(self, text: str) -> List[Dict[str, Any]]:
        r"""
        Splits text into segments by recognizing page markers:
        - `--- Page (\d+) ---`
        - `## Page (\d+)` or `# Page (\d+)`
        """
        page_pattern = re.compile(
            r'(?:^|\n)\s*(?:---\s*Page\s*(\d+)\s*---|#{1,6}\s*Page\s*(\d+))\s*(?:\n|$)',
            re.IGNORECASE
        )
        segments: List[Dict[str, Any]] = []
        current_page = 1
        last_end = 0

        for match in page_pattern.finditer(text):
            chunk_text = text[last_end:match.start()].strip()
            if chunk_text:
                segments.append({
                    "page_number": current_page,
                    "content": chunk_text
                })
            page_str = match.group(1) or match.group(2)
            if page_str:
                current_page = int(page_str)
            last_end = match.end()

        remaining = text[last_end:].strip()
        if remaining:
            segments.append({
                "page_number": current_page,
                "content": remaining
            })

        if not segments:
            segments.append({
                "page_number": 1,
                "content": text.strip()
            })

        return segments

    def _split_segment_into_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Split markdown text into sections based on headers (# ## ### etc).
        Each section includes its header and body content.
        """
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        sections: List[Dict[str, Any]] = []
        last_end = 0
        last_header = ""

        for match in header_pattern.finditer(text):
            if match.start() > last_end:
                content = text[last_end:match.start()].strip()
                if content:
                    sections.append({
                        "header": last_header,
                        "content": content,
                    })

            last_header = match.group(2).strip()
            last_end = match.end()

        remaining = text[last_end:].strip()
        if remaining:
            sections.append({
                "header": last_header,
                "content": remaining,
            })

        if not sections:
            sections.append({
                "header": "",
                "content": text.strip(),
            })

        return sections

    def _split_section_into_paragraphs(self, text: str) -> List[str]:
        """
        Split a section into paragraphs on double newlines while preserving
        markdown tables intact as single paragraphs.
        """
        raw_paragraphs = re.split(r'\n\s*\n', text)
        result: List[str] = []
        current_table_lines: List[str] = []

        for p in raw_paragraphs:
            p_strip = p.strip()
            if not p_strip:
                continue

            lines = p_strip.split("\n")
            is_table = all(l.strip().startswith("|") and l.strip().count("|") >= 2 for l in lines if l.strip())

            if is_table:
                current_table_lines.extend(lines)
            else:
                if current_table_lines:
                    result.append("\n".join(current_table_lines))
                    current_table_lines = []
                result.append(p_strip)

        if current_table_lines:
            result.append("\n".join(current_table_lines))

        return result

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences on sentence-ending punctuation."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_table_by_rows(self, table_text: str) -> List[str]:
        """
        Splits an oversized markdown table into row-based blocks,
        retaining the header row in each block to prevent breaking tables.
        """
        lines = [l for l in table_text.split("\n") if l.strip()]
        if len(lines) <= 2:
            return [table_text]

        header_lines = lines[:2]
        header_text = "\n".join(header_lines)
        header_tokens = self._estimate_tokens(header_text)
        data_rows = lines[2:]

        blocks: List[str] = []
        current_rows: List[str] = []
        current_toks = header_tokens

        for row in data_rows:
            row_toks = self._estimate_tokens(row)
            if current_toks + row_toks > self.max_tokens and current_rows:
                blocks.append(header_text + "\n" + "\n".join(current_rows))
                current_rows = [row]
                current_toks = header_tokens + row_toks
            else:
                current_rows.append(row)
                current_toks += row_toks

        if current_rows:
            blocks.append(header_text + "\n" + "\n".join(current_rows))

        return blocks or [table_text]

    def chunk_text(self, text: str) -> List[ChunkResult]:
        """
        Chunk text into overlapping segments of ~target_tokens.
        Extracts and attaches page_number and section_header to metadata.
        Preserves markdown tables without splitting rows.
        """
        if not text or not text.strip():
            return []

        page_segments = self._split_into_page_segments(text)
        chunks: List[ChunkResult] = []
        chunk_index = 0

        for segment in page_segments:
            seg_page = segment["page_number"]
            sections = self._split_segment_into_sections(segment["content"])

            current_content: List[str] = []
            current_tokens = 0
            current_header = ""

            for section in sections:
                header = section["header"]
                paragraphs = self._split_section_into_paragraphs(section["content"])

                for para in paragraphs:
                    para_tokens = self._estimate_tokens(para)
                    is_table = self._is_table_block(para)

                    # Flush if adding exceeds max_tokens
                    if current_tokens + para_tokens > self.max_tokens and current_content:
                        chunk_text = "\n\n".join(current_content)
                        chunks.append(ChunkResult(
                            chunk_index=chunk_index,
                            content=chunk_text,
                            token_count=self._estimate_tokens(chunk_text),
                            metadata={
                                "section_header": current_header or header,
                                "page_number": seg_page,
                            },
                        ))
                        chunk_index += 1

                        # Overlap
                        overlap_text = ""
                        overlap_tokens_count = 0
                        for piece in reversed(current_content):
                            if self._is_table_block(piece):
                                continue
                            piece_tokens = self._estimate_tokens(piece)
                            if overlap_tokens_count + piece_tokens > self.overlap_tokens:
                                break
                            overlap_text = piece + "\n\n" + overlap_text if overlap_text else piece
                            overlap_tokens_count += piece_tokens

                        current_content = [overlap_text] if overlap_text else []
                        current_tokens = overlap_tokens_count

                    # If this single paragraph exceeds max_tokens
                    if para_tokens > self.max_tokens:
                        if is_table:
                            table_blocks = self._split_table_by_rows(para)
                            for tblock in table_blocks:
                                tblock_tokens = self._estimate_tokens(tblock)
                                if current_tokens + tblock_tokens > self.target_tokens and current_content:
                                    chunk_text = "\n\n".join(current_content)
                                    chunks.append(ChunkResult(
                                        chunk_index=chunk_index,
                                        content=chunk_text,
                                        token_count=self._estimate_tokens(chunk_text),
                                        metadata={
                                            "section_header": current_header or header,
                                            "page_number": seg_page,
                                        },
                                    ))
                                    chunk_index += 1
                                    current_content = []
                                    current_tokens = 0
                                current_content.append(tblock)
                                current_tokens += tblock_tokens
                        else:
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
                                            "page_number": seg_page,
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

                    # Flush if reached target
                    if current_tokens >= self.target_tokens and current_content:
                        chunk_text = "\n\n".join(current_content)
                        chunks.append(ChunkResult(
                            chunk_index=chunk_index,
                            content=chunk_text,
                            token_count=self._estimate_tokens(chunk_text),
                            metadata={
                                "section_header": current_header or header,
                                "page_number": seg_page,
                            },
                        ))
                        chunk_index += 1

                        # Overlap
                        overlap_text = ""
                        overlap_tokens_count = 0
                        for piece in reversed(current_content):
                            if self._is_table_block(piece):
                                continue
                            piece_tokens = self._estimate_tokens(piece)
                            if overlap_tokens_count + piece_tokens > self.overlap_tokens:
                                break
                            overlap_text = piece + "\n\n" + overlap_text if overlap_text else piece
                            overlap_tokens_count += piece_tokens

                        current_content = [overlap_text] if overlap_text else []
                        current_tokens = overlap_tokens_count

                current_header = header

            # Flush remaining content for this page segment
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
                            "page_number": seg_page,
                        },
                    ))
                    chunk_index += 1

        logger.info(f"Chunked text into {len(chunks)} chunks (target={self.target_tokens} tokens)")
        return chunks

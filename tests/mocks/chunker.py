"""
Markdown-Aware Semantic Chunker for ApexTender v2.0 Testing & Ingestion Pipeline.
Preserves Markdown tables as atomic units, retains section context, and enforces token bounds.
"""

import re
from typing import List, Dict, Any, Optional

class SemanticChunker:
    def __init__(self, target_tokens: int = 600, overlap_tokens: int = 100):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def chunk_markdown(self, markdown: str) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        if not markdown or not markdown.strip():
            return chunks

        # Split on Markdown headers (#, ##, ###, ####)
        section_regex = r'(?=^#{1,4}\s+.*$)'
        raw_sections = [s for s in re.split(section_regex, markdown, flags=re.MULTILINE) if s.strip()]

        current_chunk_index = 0
        active_header = "General Information"

        for section in raw_sections:
            header_match = re.search(r'^#{1,4}\s+(.*)$', section, flags=re.MULTILINE)
            if header_match:
                active_header = header_match.group(1).strip()

            section_tokens = self.estimate_tokens(section)

            if section_tokens <= self.target_tokens:
                chunks.append({
                    "chunk_index": current_chunk_index,
                    "content": section.strip(),
                    "page_number": self._extract_page_number(section),
                    "section_header": active_header,
                    "has_table": ("|---" in section or "|:--" in section or "| :--" in section or "| ---" in section),
                    "token_count": section_tokens,
                })
                current_chunk_index += 1
            else:
                sub_blocks = self._split_into_sub_blocks(section)
                buffer = ""
                buffer_tokens = 0

                for block in sub_blocks:
                    block_tokens = self.estimate_tokens(block)

                    if buffer_tokens + block_tokens > self.target_tokens and len(buffer) > 0:
                        chunks.append({
                            "chunk_index": current_chunk_index,
                            "content": buffer.strip(),
                            "page_number": self._extract_page_number(buffer),
                            "section_header": active_header,
                            "has_table": ("|---" in buffer or "|:--" in buffer or "| :--" in buffer or "| ---" in buffer),
                            "token_count": buffer_tokens,
                        })
                        current_chunk_index += 1

                        words = buffer.split()
                        overlap_count = max(5, int(self.overlap_tokens * 0.75))
                        overlap_words = " ".join(words[-overlap_count:])
                        buffer = f"[Context: {active_header}]\n... {overlap_words}\n\n" + block
                        buffer_tokens = self.estimate_tokens(buffer)
                    else:
                        buffer = (buffer + "\n\n" + block) if buffer else block
                        buffer_tokens += block_tokens

                if buffer.strip():
                    chunks.append({
                        "chunk_index": current_chunk_index,
                        "content": buffer.strip(),
                        "page_number": self._extract_page_number(buffer),
                        "section_header": active_header,
                        "has_table": ("|---" in buffer or "|:--" in buffer or "| :--" in buffer or "| ---" in buffer),
                        "token_count": buffer_tokens,
                    })
                    current_chunk_index += 1

        return chunks

    def _split_into_sub_blocks(self, text: str) -> List[str]:
        lines = text.split("\n")
        blocks: List[str] = []
        current_table: List[str] = []
        current_para: List[str] = []

        for line in lines:
            if line.strip().startswith("|"):
                if current_para:
                    blocks.append("\n".join(current_para))
                    current_para = []
                current_table.append(line)
            else:
                if current_table:
                    blocks.append("\n".join(current_table))
                    current_table = []
                if line.strip() == "":
                    if current_para:
                        blocks.append("\n".join(current_para))
                        current_para = []
                else:
                    current_para.append(line)

        if current_table:
            blocks.append("\n".join(current_table))
        if current_para:
            blocks.append("\n".join(current_para))

        return [b for b in blocks if b.strip()]

    def _extract_page_number(self, text: str) -> Optional[int]:
        match = re.search(r'(?:Page|PAGE|page)\s+(\d+)', text)
        return int(match.group(1)) if match else 1

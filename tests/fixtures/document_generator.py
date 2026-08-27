"""
Document and Payload Generator for ApexTender v2.0 Boundary & Stress Testing.
Generates large files (>10MB), empty documents, corrupted binaries, and structured pages.
"""

import os
from typing import Dict, Any, List

def generate_large_file_bytes(size_in_mb: float = 12.0, pattern: str = "Enterprise RFP Data Block ") -> bytes:
    """
    Generates binary or text payload of exact size in MB.
    """
    target_bytes = int(size_in_mb * 1024 * 1024)
    pattern_bytes = pattern.encode("utf-8")
    repeat_count = target_bytes // len(pattern_bytes)
    remainder = target_bytes % len(pattern_bytes)
    return (pattern_bytes * repeat_count) + pattern_bytes[:remainder]

def generate_corrupted_pdf_bytes() -> bytes:
    """
    Returns malformed PDF header and invalid byte stream.
    """
    return b"%PDF-1.7\n\x00\xff\xfe\x00CORRUPT_BODY_TRUNCATED_STREAM"

def generate_empty_bytes() -> bytes:
    """
    Returns 0-byte file.
    """
    return b""

def generate_multi_page_rfp_text(num_pages: int = 10, sections_per_page: int = 2) -> str:
    """
    Generates multi-page Markdown text with distinct headers and tables for chunker testing.
    """
    pages = []
    for p in range(1, num_pages + 1):
        page_lines = [f"## Page {p}"]
        for s in range(1, sections_per_page + 1):
            sec_num = f"{p}.{s}"
            page_lines.append(f"### Section {sec_num}: Technical Criteria {sec_num}")
            page_lines.append(
                f"The contractor must deliver milestone {sec_num} within specified SLA guidelines. "
                f"All security controls in section {sec_num} are mandatory."
            )
            page_lines.append(
                f"| Parameter | Value {sec_num} | Minimum Score |\n"
                f"| :--- | :--- | :--- |\n"
                f"| Performance Benchmark | 99.{p}% | Level {s} |\n"
                f"| SLA Penalty | {p}% | Mandatory |\n"
            )
        pages.append("\n\n".join(page_lines))
    return "\n\n".join(pages)

def generate_docx_mock_bytes() -> bytes:
    """
    Returns mock DOCX zip-like header.
    """
    return b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00DOCX_DOCUMENT_XML_MOCK"

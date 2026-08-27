"""
Mock LlamaParse Cloud Service for ApexTender v2.0 E2E Testing.
Emulates LlamaParse document extraction API:
- POST /api/parsing/upload
- GET /api/parsing/job/{job_id}
- GET /api/parsing/job/{job_id}/result/markdown
Provides programmable error injection (429 rate limit, 402 quota exhausted, polling timeout, corrupt data).
"""

import uuid
from typing import Dict, Any, Optional

class MockLlamaParseService:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.mode = "success"  # "success", "429_rate_limit", "402_quota_exhausted", "timeout", "parse_error"
        self.poll_delay_count = 0
        self.required_polls = 1

    def set_mode(self, mode: str, required_polls: int = 1):
        """
        Configure mock mode:
        - 'success': Normal parsing to Markdown with structured tables.
        - '429_rate_limit': Simulates HTTP 429 Too Many Requests.
        - '402_quota_exhausted': Simulates HTTP 402 / 403 Free Tier Quota Exhausted.
        - 'timeout': Keeps job in 'PENDING' until timeout.
        - 'parse_error': Returns 'ERROR' status on job polling.
        """
        self.mode = mode
        self.required_polls = required_polls

    def upload_file(self, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Emulates POST https://api.cloud.llamaindex.ai/api/parsing/upload
        """
        if self.mode == "429_rate_limit":
            return {"status_code": 429, "error": "LlamaParse 429: Too Many Requests"}
        if self.mode == "402_quota_exhausted":
            return {"status_code": 402, "error": "LlamaParse 402: Free tier daily credits exhausted (1,000 pages limit)"}

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Synthesize parsed markdown from file contents or sample RFP markdown
        file_text = ""
        try:
            file_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            file_text = "Binary PDF Content"

        # Generate structured markdown with RFP tables and headings
        if "# " in file_text or "| " in file_text:
            parsed_markdown = file_text
        else:
            parsed_markdown = (
                f"# Enterprise RFP Document: {filename}\n\n"
                f"## 1.0 Executive Summary\n"
                f"This Request for Proposal (RFP) defines the terms, technical requirements, and evaluation criteria.\n\n"
                f"## 2.0 Service Level Agreements (SLAs) & Penalties\n"
                f"| Tier | Availability Target | Response Time | Penalty Deduction |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| Tier 1 (Mission Critical) | 99.99% | < 15 minutes | 5% monthly fee credit |\n"
                f"| Tier 2 (Standard) | 99.9% | < 1 hour | 2% monthly fee credit |\n"
                f"| Tier 3 (Non-Urgent) | 99.5% | < 4 hours | 1% monthly fee credit |\n\n"
                f"## 3.0 Cybersecurity & Compliance\n"
                f"The contractor must maintain FedRAMP High Authorization, SOC 2 Type II certification, and GDPR Article 28 data processing safeguards.\n\n"
                f"## 4.0 Pricing & Evaluation Matrix\n"
                f"| Deliverable | Milestone | Cost Allocation |\n"
                f"| :--- | :--- | :--- |\n"
                f"| Phase 1: Architecture & Security | Month 1 | $150,000 |\n"
                f"| Phase 2: Ingestion & Vector Search | Month 3 | $350,000 |\n"
                f"| Phase 3: Production Deployment | Month 6 | $250,000 |\n"
            )

        self.jobs[job_id] = {
            "id": job_id,
            "filename": filename,
            "polls": 0,
            "markdown": parsed_markdown,
            "mode": self.mode
        }
        
        return {"status_code": 200, "id": job_id, "status": "PENDING"}

    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Emulates GET https://api.cloud.llamaindex.ai/api/parsing/job/{job_id}
        """
        job = self.jobs.get(job_id)
        if not job:
            return {"status_code": 404, "error": "Job not found"}

        if self.mode == "429_rate_limit":
            return {"status_code": 429, "error": "Rate limit during polling"}
        if self.mode == "timeout":
            return {"status_code": 200, "id": job_id, "status": "PENDING"}
        if self.mode == "parse_error":
            return {"status_code": 200, "id": job_id, "status": "ERROR", "error_message": "Corrupt PDF stream"}

        job["polls"] += 1
        if job["polls"] >= self.required_polls:
            return {"status_code": 200, "id": job_id, "status": "SUCCESS"}
        else:
            return {"status_code": 200, "id": job_id, "status": "PENDING"}

    def get_job_result_markdown(self, job_id: str) -> Dict[str, Any]:
        """
        Emulates GET https://api.cloud.llamaindex.ai/api/parsing/job/{job_id}/result/markdown
        """
        job = self.jobs.get(job_id)
        if not job:
            return {"status_code": 404, "error": "Job not found"}
        if job.get("mode") == "parse_error":
            return {"status_code": 400, "error": "Job failed"}

        return {
            "status_code": 200,
            "markdown": job["markdown"]
        }

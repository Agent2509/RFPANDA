// ============================================================================
// ApexTender v2.0 — Chunker Unit Tests (Deno Test Runner)
// ============================================================================

import {
  assert,
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.177.0/testing/asserts.ts";
import { SemanticChunker } from "../_shared/chunker.ts";

Deno.test("SemanticChunker: Empty or blank text returns empty array", () => {
  const chunker = new SemanticChunker();
  assertEquals(chunker.chunkMarkdown(""), []);
  assertEquals(chunker.chunkMarkdown("   \n\n  \t  "), []);
});

Deno.test("SemanticChunker: Short markdown document returns 1 chunk", () => {
  const chunker = new SemanticChunker({ targetTokens: 600 });
  const text =
    `# 1.0 Project Overview\n\nThis is a short RFP document describing the software delivery timeline.`;
  const chunks = chunker.chunkMarkdown(text);

  assertEquals(chunks.length, 1);
  assertEquals(chunks[0].chunkIndex, 0);
  assertEquals(chunks[0].sectionHeader, "1.0 Project Overview");
  assert(chunks[0].content.includes("software delivery timeline"));
  assert(chunks[0].tokenCount > 0);
});

Deno.test("SemanticChunker: Preserves Markdown table rows intact", () => {
  const chunker = new SemanticChunker({ targetTokens: 200 });
  const tableMd = `
# Section 2: Pricing Schedule

| Item | Description | Unit Price | Total |
| :--- | :---------- | :--------- | :---- |
| 1    | Cloud Engine | $500       | $500  |
| 2    | Vector DB   | $200       | $200  |
| 3    | SLA Support | $300       | $300  |
`;

  const chunks = chunker.chunkMarkdown(tableMd);
  assert(chunks.length >= 1);

  const tableChunk = chunks.find((c) => c.hasTable);
  assertExists(
    tableChunk,
    "Expected at least one chunk to have hasTable = true",
  );
  assert(
    tableChunk.content.includes("| Item | Description | Unit Price | Total |"),
  );
  assert(
    tableChunk.content.includes("| 1    | Cloud Engine | $500       | $500  |"),
  );
  assert(
    tableChunk.content.includes("| 3    | SLA Support | $300       | $300  |"),
  );
});

Deno.test("SemanticChunker: Large Markdown table is split with header repeated", () => {
  const chunker = new SemanticChunker({ targetTokens: 80, maxTokens: 120 });

  // Construct a large table with 30 rows
  const rows: string[] = [];
  rows.push("| Metric ID | SLA Requirement | Target Value | Penalty |");
  rows.push("| :-------- | :-------------- | :----------- | :------ |");
  for (let i = 1; i <= 30; i++) {
    rows.push(
      `| SLA-${
        i.toString().padStart(3, "0")
      } | System uptime and latency guarantee for service tier ${i} | 99.9${
        i % 9
      }% | 5% deduction per outage |`,
    );
  }

  const tableDoc = `# 3.0 SLA Compliance Matrix\n\n` + rows.join("\n");
  const chunks = chunker.chunkMarkdown(tableDoc);

  assert(
    chunks.length > 1,
    `Expected multiple chunks for large table, got ${chunks.length}`,
  );

  for (const chunk of chunks) {
    assert(
      chunk.hasTable,
      "Every sub-chunk of large table should have hasTable = true",
    );
    assert(
      chunk.content.includes(
        "| Metric ID | SLA Requirement | Target Value | Penalty |",
      ),
      "Every sub-chunk must replicate the table header row",
    );
    assert(
      chunk.content.includes(
        "| :-------- | :-------------- | :----------- | :------ |",
      ) ||
        chunk.content.includes("|---|---|---|---|"),
      "Every sub-chunk must replicate the separator row",
    );
  }
});

Deno.test("SemanticChunker: Preserves Section Header hierarchy and context", () => {
  const chunker = new SemanticChunker({ targetTokens: 50, maxTokens: 80 });
  const text = `
# 1.0 Executive Summary
This section outlines the high level goals.

## 1.1 Technical Scope
The contractor must deliver a scalable microservice architecture.

### 1.1.1 Security Protocols
All communication must be encrypted using TLS 1.3. AES-256 is required at rest. Multi-factor authentication is mandatory for administrative accounts.
`;

  const chunks = chunker.chunkMarkdown(text);
  assert(chunks.length >= 2);

  // Check that security chunk has section hierarchy or breadcrumb
  const securityChunk = chunks.find((c) =>
    c.content.includes("AES-256") || c.content.includes("TLS 1.3")
  );
  assertExists(securityChunk);
  assert(
    securityChunk.sectionHeader?.includes("Security Protocols") ||
      securityChunk.content.includes("Security Protocols"),
  );
});

Deno.test("SemanticChunker: Extracts page numbers accurately", () => {
  const chunker = new SemanticChunker({ targetTokens: 600 });
  const pageDoc = `
## Page 1
# Introduction
Welcome to the RFP requirements.

---

## Page 2
# Detailed Specifications
Here are the server specifications.
`;

  const chunks = chunker.chunkMarkdown(pageDoc);
  assert(chunks.length >= 1);

  const page1Chunk = chunks.find((c) =>
    c.content.includes("Welcome to the RFP")
  );
  assertExists(page1Chunk);
  assertEquals(page1Chunk.pageNumber, 1);

  const page2Chunk = chunks.find((c) =>
    c.content.includes("server specifications")
  );
  assertExists(page2Chunk);
  assertEquals(page2Chunk.pageNumber, 2);
});

Deno.test("SemanticChunker: Preserves code blocks intact", () => {
  const chunker = new SemanticChunker({ targetTokens: 300 });
  const codeDoc = `
# API Integration Guide

\`\`\`json
{
  "api_version": "2.0",
  "auth": "Bearer token",
  "endpoints": ["/api/v1/query", "/api/v1/status"]
}
\`\`\`
`;

  const chunks = chunker.chunkMarkdown(codeDoc);
  assertEquals(chunks.length, 1);
  assert(chunks[0].content.includes("```json"));
  assert(chunks[0].content.includes('"api_version": "2.0"'));
  assert(chunks[0].content.includes("```"));
});

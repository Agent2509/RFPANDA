// ============================================================================
// RFPANDA — Edge Functions Integration / Handler Unit Tests
// ============================================================================

import {
  assert,
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.177.0/testing/asserts.ts";
import { handleCors, jsonResponse } from "../_shared/cors.ts";
import { SemanticChunker } from "../_shared/chunker.ts";
import { VoyageClient } from "../_shared/voyage.ts";
import { LlamaParseClient } from "../_shared/llamaparse.ts";

Deno.test("CORS Helper: Handles OPTIONS request properly", () => {
  const optionsReq = new Request(
    "https://test.supabase.co/functions/v1/process-document",
    {
      method: "OPTIONS",
    },
  );
  const res = handleCors(optionsReq);
  assertExists(res);
  assertEquals(res.status, 200);
  assertEquals(res.headers.get("Access-Control-Allow-Origin"), "*");
});

Deno.test("CORS Helper: Returns null for non-OPTIONS requests", () => {
  const postReq = new Request(
    "https://test.supabase.co/functions/v1/process-document",
    {
      method: "POST",
    },
  );
  const res = handleCors(postReq);
  assertEquals(res, null);
});

Deno.test("CORS Helper: jsonResponse attaches CORS and content-type headers", async () => {
  const res = jsonResponse({ status: "ok" }, 201);
  assertEquals(res.status, 201);
  assertEquals(res.headers.get("Access-Control-Allow-Origin"), "*");
  assertEquals(res.headers.get("Content-Type"), "application/json");

  const json = await res.json();
  assertEquals(json, { status: "ok" });
});

Deno.test("End-to-End Flow: Fallback Ingestion Pipeline Logic Simulation", async () => {
  // 1. Simulate client-side PDF.js extracted text
  const pdfJsExtractedText = `
## Page 1
# Section 1: RFP Requirements for Cloud Hosting

The contractor shall provide a secure high-availability cloud architecture.
Uptime must be at least 99.95% measured monthly.

| Requirement ID | Service Component | Min RAM | Storage Type |
| :--- | :--- | :--- | :--- |
| REQ-001 | Vector Processing Node | 16 GB | NVMe SSD |
| REQ-002 | Database Replica | 32 GB | High-IOPS SSD |
| REQ-003 | Edge Routing Layer | 8 GB | Standard SSD |

---

## Page 2
# Section 2: Security and Compliance

All data in transit must use TLS 1.3 encryption.
Audit logging must retain records for a minimum of 365 days.
`;

  // 2. Chunker parses text
  const chunker = new SemanticChunker({
    targetTokens: 400,
    overlapTokens: 50,
    maxTokens: 800,
  });
  const chunks = chunker.chunkMarkdown(pdfJsExtractedText);

  assert(
    chunks.length >= 2,
    `Expected at least 2 chunks, got ${chunks.length}`,
  );
  const tableChunk = chunks.find((c) => c.hasTable);
  assertExists(tableChunk, "Table chunk should exist");
  assert(
    tableChunk.content.includes(
      "| REQ-001 | Vector Processing Node | 16 GB | NVMe SSD |",
    ),
  );

  // 3. Mock Voyage AI embeddings
  const originalFetch = globalThis.fetch;
  let voyagePayloadInputs: string[] = [];

  globalThis.fetch = (
    input: string | URL | Request,
    init?: RequestInit,
  ): Promise<Response> => {
    const url = input.toString();
    if (url.includes("voyageai")) {
      const body = JSON.parse(init?.body as string);
      voyagePayloadInputs = body.input;
      return Promise.resolve(
        new Response(
          JSON.stringify({
            object: "list",
            data: body.input.map((_: string, idx: number) => ({
              object: "embedding",
              embedding: new Array(1024).fill(0.01 * (idx + 1)),
              index: idx,
            })),
            model: "voyage-3-lite",
            usage: { total_tokens: body.input.length * 40 },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  };

  try {
    const voyageClient = new VoyageClient({
      apiKey: "voyage_test_key",
      baseUrl: "https://api.voyageai.com/v1/embeddings",
    });

    const { embeddings, totalTokens } = await voyageClient.embedChunks(
      chunks.map((c) => c.content),
      64,
    );

    assertEquals(embeddings.length, chunks.length);
    assertEquals(embeddings[0].length, 1024);
    assert(totalTokens > 0);
    assertEquals(voyagePayloadInputs.length, chunks.length);

    // 4. Simulate pgvector Document Chunk Row Generation
    const fakeDocId = "8b7d91e2-5678-4321-98ba-dcba98765432";
    const fakeUserId = "a3f2e1c0-1234-4567-89ab-cdef01234567";

    const chunkRows = chunks.map((chunk, idx) => ({
      document_id: fakeDocId,
      user_id: fakeUserId,
      chunk_index: chunk.chunkIndex,
      content: chunk.content,
      embedding: embeddings[idx],
      token_count: chunk.tokenCount,
      metadata: {
        ...chunk.metadata,
        parser: "pdfjs_client_fallback",
      },
    }));

    assertEquals(chunkRows.length, chunks.length);
    assertEquals(chunkRows[0].document_id, fakeDocId);
    assertEquals(chunkRows[0].user_id, fakeUserId);
    assertEquals(chunkRows[0].embedding.length, 1024);
    assertEquals(chunkRows[0].metadata.parser, "pdfjs_client_fallback");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("End-to-End Flow: Primary LlamaParse 429 Graceful Degradation Simulation", async () => {
  // Simulate LlamaParse 429 Rate Limit
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (input: string | URL | Request): Promise<Response> => {
    const url = input.toString();
    if (url.includes("upload")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            detail: "Concurrent request limit reached on free tier",
          }),
          { status: 429, headers: { "Content-Type": "application/json" } },
        ),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  };

  try {
    const llamaClient = new LlamaParseClient({
      apiKey: "llama_test_key",
      uploadUrl: "https://api.cloud.llamaindex.ai/api/parsing/upload",
    });

    const fileBlob = new Blob(["sample binary pdf"], {
      type: "application/pdf",
    });
    const parseResult = await llamaClient.parseFile(fileBlob, "contract.pdf");

    assertEquals(parseResult.success, false);
    assertEquals(parseResult.errorType, "rate_limit");

    // Simulate Edge Function Decision Logic
    const isFallbackEligible = parseResult.errorType === "rate_limit" ||
      parseResult.errorType === "quota_exhausted" ||
      parseResult.errorType === "timeout";

    assertEquals(isFallbackEligible, true);

    const resultingDocumentStatus = isFallbackEligible
      ? "awaiting_fallback_parse"
      : "failed";
    assertEquals(resultingDocumentStatus, "awaiting_fallback_parse");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

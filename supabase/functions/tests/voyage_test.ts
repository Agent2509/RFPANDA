// ============================================================================
// RFPANDA — VoyageClient Unit Tests (Deno Test Runner)
// ============================================================================

import {
  assertEquals,
  assertRejects,
} from "https://deno.land/std@0.177.0/testing/asserts.ts";
import { VoyageClient } from "../_shared/voyage.ts";

Deno.test("VoyageClient: Empty inputs return empty array", async () => {
  const client = new VoyageClient({ apiKey: "mock_key" });
  const res = await client.embedChunks([]);
  assertEquals(res.embeddings, []);
  assertEquals(res.totalTokens, 0);
});

Deno.test("VoyageClient: Batches requests exceeding batchSize", async () => {
  let callCount = 0;
  const requestedBatchSizes: number[] = [];

  // Mock global fetch
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (
    _input: string | URL | Request,
    init?: RequestInit,
  ): Promise<Response> => {
    callCount++;
    const body = JSON.parse(init?.body as string);
    requestedBatchSizes.push(body.input.length);

    assertEquals(body.model, "voyage-3-lite");
    assertEquals(body.input_type, "document");
    assertEquals(body.output_dimension, 1024);

    const mockEmbeddings = body.input.map((_: string, idx: number) => ({
      object: "embedding",
      embedding: new Array(1024).fill(0.01 * (idx + 1)),
      index: idx,
    }));

    return Promise.resolve(
      new Response(
        JSON.stringify({
          object: "list",
          data: mockEmbeddings,
          model: "voyage-3-lite",
          usage: { total_tokens: body.input.length * 10 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  };

  try {
    const client = new VoyageClient({
      apiKey: "mock_voyage_key",
      baseUrl: "https://mock.voyage.api/v1/embeddings",
    });
    const testTexts = Array.from(
      { length: 150 },
      (_, i) => `Sample RFP text chunk #${i + 1}`,
    );

    const result = await client.embedChunks(testTexts, 64);

    // 150 items with batchSize 64 should result in 3 calls: 64, 64, 22
    assertEquals(callCount, 3);
    assertEquals(requestedBatchSizes, [64, 64, 22]);
    assertEquals(result.embeddings.length, 150);
    assertEquals(result.embeddings[0].length, 1024);
    assertEquals(result.totalTokens, 1500);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("VoyageClient: Retries on 429 Rate Limit with exponential backoff", async () => {
  let attempts = 0;
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (
    _input: string | URL | Request,
    init?: RequestInit,
  ): Promise<Response> => {
    attempts++;
    if (attempts < 3) {
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Rate limit exceeded" }), {
          status: 429,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }

    const body = JSON.parse(init?.body as string);
    const mockEmbeddings = body.input.map((_: string, idx: number) => ({
      object: "embedding",
      embedding: new Array(1024).fill(0.05),
      index: idx,
    }));

    return Promise.resolve(
      new Response(
        JSON.stringify({
          object: "list",
          data: mockEmbeddings,
          model: "voyage-3-lite",
          usage: { total_tokens: 50 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  };

  try {
    const client = new VoyageClient({
      apiKey: "test_key",
      baseUrl: "https://mock.voyage.api",
      maxRetries: 3,
      initialBackoffMs: 20,
    });

    const result = await client.embedChunks(["Test chunk"]);
    assertEquals(attempts, 3);
    assertEquals(result.embeddings.length, 1);
    assertEquals(result.embeddings[0].length, 1024);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("VoyageClient: Throws error on permanent 400 Bad Request", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (): Promise<Response> => {
    return Promise.resolve(
      new Response(JSON.stringify({ detail: "Invalid model specified" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }),
    );
  };

  try {
    const client = new VoyageClient({
      apiKey: "test_key",
      baseUrl: "https://mock.voyage.api",
      maxRetries: 2,
      initialBackoffMs: 10,
    });

    await assertRejects(
      async () => {
        await client.embedChunks(["Test chunk"]);
      },
      Error,
      "Voyage AI API Error (HTTP 400)",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

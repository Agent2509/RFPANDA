// ============================================================================
// ApexTender v2.0 — LlamaParseClient Unit Tests (Deno Test Runner)
// ============================================================================

import {
  assert,
  assertEquals,
} from "https://deno.land/std@0.177.0/testing/asserts.ts";
import { LlamaParseClient } from "../_shared/llamaparse.ts";

Deno.test("LlamaParseClient: Missing API key returns quota_exhausted error", async () => {
  const client = new LlamaParseClient({ apiKey: "" });
  const fakeBlob = new Blob(["sample pdf content"], {
    type: "application/pdf",
  });
  const result = await client.parseFile(fakeBlob, "test.pdf");

  assertEquals(result.success, false);
  assertEquals(result.errorType, "quota_exhausted");
});

Deno.test("LlamaParseClient: Successful file parse with polling and markdown extraction", async () => {
  const originalFetch = globalThis.fetch;
  let uploadCalled = false;
  let pollCount = 0;
  let resultCalled = false;

  globalThis.fetch = (
    input: string | URL | Request,
    init?: RequestInit,
  ): Promise<Response> => {
    const url = input.toString();

    if (url.includes("/api/parsing/upload")) {
      uploadCalled = true;
      assertEquals(init?.method, "POST");
      assert(init?.headers);
      return Promise.resolve(
        new Response(JSON.stringify({ id: "job_12345", status: "PENDING" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }

    if (url.includes("/api/parsing/job/job_12345/result/markdown")) {
      resultCalled = true;
      return Promise.resolve(
        new Response(
          JSON.stringify({
            markdown:
              "# Section 1: RFP Requirements\n\n| Item | Spec |\n|---|---|\n| RAM | 32GB |\n",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    }

    if (url.includes("/api/parsing/job/job_12345")) {
      pollCount++;
      if (pollCount === 1) {
        return Promise.resolve(
          new Response(JSON.stringify({ status: "PROCESSING" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ status: "SUCCESS", num_pages: 2 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }

    return Promise.resolve(new Response("Not Found", { status: 404 }));
  };

  try {
    const client = new LlamaParseClient({
      apiKey: "test_llama_key",
      uploadUrl: "https://mock.llamaindex.ai/api/parsing/upload",
      jobUrl: "https://mock.llamaindex.ai/api/parsing/job",
      initialPollDelayMs: 10,
      pollIntervalMs: 10,
      maxWaitMs: 2000,
    });

    const fakeBlob = new Blob(["pdf data"], { type: "application/pdf" });
    const result = await client.parseFile(fakeBlob, "dod_rfp.pdf");

    assert(uploadCalled);
    assert(resultCalled);
    assertEquals(pollCount, 2);
    assertEquals(result.success, true);
    assertEquals(result.jobId, "job_12345");
    assert(result.markdown?.includes("# Section 1: RFP Requirements"));
    assert(result.markdown?.includes("| RAM | 32GB |"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("LlamaParseClient: Classifies HTTP 429 as rate_limit error", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (input: string | URL | Request): Promise<Response> => {
    const url = input.toString();
    if (url.includes("/upload")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            detail: "Rate limit exceeded: max 5 concurrent jobs",
          }),
          {
            status: 429,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  };

  try {
    const client = new LlamaParseClient({
      apiKey: "test_key",
      uploadUrl: "https://mock.llamaindex.ai/upload",
      jobUrl: "https://mock.llamaindex.ai/job",
    });

    const fakeBlob = new Blob(["data"], { type: "application/pdf" });
    const result = await client.parseFile(fakeBlob, "test.pdf");

    assertEquals(result.success, false);
    assertEquals(result.errorType, "rate_limit");
    assert(result.errorMessage?.includes("429"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("LlamaParseClient: Classifies HTTP 402/403 as quota_exhausted error", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (input: string | URL | Request): Promise<Response> => {
    const url = input.toString();
    if (url.includes("/upload")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            detail: "Credit balance zero: please upgrade plan",
          }),
          {
            status: 402,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  };

  try {
    const client = new LlamaParseClient({
      apiKey: "test_key",
      uploadUrl: "https://mock.llamaindex.ai/upload",
      jobUrl: "https://mock.llamaindex.ai/job",
    });

    const fakeBlob = new Blob(["data"], { type: "application/pdf" });
    const result = await client.parseFile(fakeBlob, "test.pdf");

    assertEquals(result.success, false);
    assertEquals(result.errorType, "quota_exhausted");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test("LlamaParseClient: Classifies timeout when job does not finish within maxWaitMs", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (input: string | URL | Request): Promise<Response> => {
    const url = input.toString();
    if (url.includes("/upload")) {
      return Promise.resolve(
        new Response(JSON.stringify({ id: "slow_job_999" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    if (url.includes("/job/slow_job_999")) {
      return Promise.resolve(
        new Response(JSON.stringify({ status: "PROCESSING" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  };

  try {
    const client = new LlamaParseClient({
      apiKey: "test_key",
      uploadUrl: "https://mock.llamaindex.ai/upload",
      jobUrl: "https://mock.llamaindex.ai/job",
      initialPollDelayMs: 10,
      pollIntervalMs: 20,
      maxWaitMs: 80,
    });

    const fakeBlob = new Blob(["data"], { type: "application/pdf" });
    const result = await client.parseFile(fakeBlob, "test.pdf");

    assertEquals(result.success, false);
    assertEquals(result.errorType, "timeout");
    assertEquals(result.jobId, "slow_job_999");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

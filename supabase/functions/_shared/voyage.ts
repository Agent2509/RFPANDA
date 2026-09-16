// ============================================================================
// ApexTender v2.0 — Voyage AI Embedding REST Client
// ============================================================================

export interface EmbeddingResult {
  embeddings: number[][];
  totalTokens: number;
}

export interface VoyageClientOptions {
  apiKey?: string;
  model?: string;
  baseUrl?: string;
  maxRetries?: number;
  initialBackoffMs?: number;
}

export interface VoyageEmbeddingResponse {
  object: string;
  data: Array<{
    object: string;
    embedding: number[];
    index: number;
  }>;
  model: string;
  usage?: {
    total_tokens?: number;
  };
}

export class VoyageClient {
  private apiKey: string;
  private model: string;
  private baseUrl: string;
  private maxRetries: number;
  private initialBackoffMs: number;

  constructor(
    apiKeyOrOptions?: string | VoyageClientOptions,
    model = "voyage-3",
  ) {
    if (typeof apiKeyOrOptions === "string") {
      this.apiKey = apiKeyOrOptions;
      this.model = model;
      this.baseUrl = Deno.env.get("VOYAGE_API_URL") ||
        "https://api.voyageai.com/v1/embeddings";
      this.maxRetries = 4;
      this.initialBackoffMs = 1000;
    } else {
      const opts = apiKeyOrOptions || {};
      this.apiKey = opts.apiKey || Deno.env.get("VOYAGE_API_KEY") || "";
      this.model = opts.model || "voyage-3";
      this.baseUrl = opts.baseUrl ||
        Deno.env.get("VOYAGE_API_URL") ||
        "https://api.voyageai.com/v1/embeddings";
      this.maxRetries = opts.maxRetries ?? 4;
      this.initialBackoffMs = opts.initialBackoffMs ?? 1000;
    }

    if (!this.apiKey && !Deno.env.get("VOYAGE_API_KEY")) {
      console.warn("[VoyageClient] Warning: VOYAGE_API_KEY is not set.");
    }
  }

  /**
   * Generates 1024-dimensional embeddings for an array of text chunks.
   * Chunks are automatically sliced into batches (default 64) with exponential retry.
   */
  public async embedChunks(
    texts: string[],
    batchSize = 64,
  ): Promise<EmbeddingResult> {
    if (!texts || texts.length === 0) {
      return { embeddings: [], totalTokens: 0 };
    }

    // Enforce batch size bound (Voyage AI limit is 128)
    const effectiveBatchSize = Math.min(Math.max(1, batchSize), 128);
    const allEmbeddings: number[][] = [];
    let totalTokens = 0;

    for (let i = 0; i < texts.length; i += effectiveBatchSize) {
      const batch = texts.slice(i, i + effectiveBatchSize);
      const res = await this.callEmbeddingApi(batch);

      // Sort by index to guarantee input ordering
      const sortedData = [...res.data].sort((a, b) => a.index - b.index);
      for (const item of sortedData) {
        allEmbeddings.push(item.embedding);
      }

      totalTokens += res.usage?.total_tokens ?? 0;
    }

    return {
      embeddings: allEmbeddings,
      totalTokens,
    };
  }

  /**
   * Internal API caller with exponential backoff on 429 and transient errors.
   */
  private async callEmbeddingApi(
    inputs: string[],
    attempt = 1,
  ): Promise<VoyageEmbeddingResponse> {
    const key = this.apiKey || Deno.env.get("VOYAGE_API_KEY") || "";
    if (!key) {
      throw new Error(
        "Voyage AI API Key is required. Set VOYAGE_API_KEY environment variable.",
      );
    }

    const payload = {
      model: this.model,
      input: inputs,
      input_type: "document",
      output_dimension: 1024,
      truncation: true,
    };

    try {
      const res = await fetch(this.baseUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${key}`,
        },
        body: JSON.stringify(payload),
      });

      // Handle Rate Limiting (429) or Transient Server Errors (500, 502, 503, 504)
      if (
        (res.status === 429 || res.status >= 500) && attempt <= this.maxRetries
      ) {
        const jitter = Math.floor(Math.random() * 300);
        const delay = this.initialBackoffMs * Math.pow(2, attempt - 1) + jitter;
        console.warn(
          `[VoyageClient] Status ${res.status}. Retrying attempt ${attempt}/${this.maxRetries} after ${delay}ms...`,
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.callEmbeddingApi(inputs, attempt + 1);
      }

      if (!res.ok) {
        const errorText = await res.text().catch(() => "Unknown error");
        throw new Error(
          `Voyage AI API Error (HTTP ${res.status}): ${errorText}`,
        );
      }

      const data: VoyageEmbeddingResponse = await res.json();
      if (!data.data || !Array.isArray(data.data)) {
        throw new Error(
          `Voyage AI returned invalid response structure: ${
            JSON.stringify(data)
          }`,
        );
      }

      return data;
    } catch (err: unknown) {
      const error = err as Error;
      if (
        attempt <= this.maxRetries &&
        !error.message?.includes("API Error (HTTP 401)") &&
        !error.message?.includes("API Error (HTTP 400)")
      ) {
        const jitter = Math.floor(Math.random() * 300);
        const delay = this.initialBackoffMs * Math.pow(2, attempt - 1) + jitter;
        console.warn(
          `[VoyageClient] Network error "${error.message}". Retrying attempt ${attempt}/${this.maxRetries} after ${delay}ms...`,
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.callEmbeddingApi(inputs, attempt + 1);
      }
      throw error;
    }
  }
}

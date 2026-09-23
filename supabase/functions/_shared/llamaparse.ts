// ============================================================================
// RFPANDA — LlamaParse Client with Error Classification & Fallback Trigger
// ============================================================================

export type LlamaParseErrorType =
  | "rate_limit"
  | "quota_exhausted"
  | "timeout"
  | "parsing_failed";

export interface LlamaParseResult {
  success: boolean;
  markdown?: string;
  errorType?: LlamaParseErrorType;
  errorMessage?: string;
  jobId?: string;
  pagesCount?: number;
}

export interface LlamaParseClientOptions {
  apiKey?: string;
  uploadUrl?: string;
  jobUrl?: string;
  maxWaitMs?: number;
  initialPollDelayMs?: number;
  pollIntervalMs?: number;
}

export class LlamaParseClient {
  private apiKey: string;
  private uploadUrl: string;
  private jobUrl: string;
  private maxWaitMs: number;
  private initialPollDelayMs: number;
  private pollIntervalMs: number;

  constructor(apiKeyOrOptions?: string | LlamaParseClientOptions) {
    if (typeof apiKeyOrOptions === "string") {
      this.apiKey = apiKeyOrOptions;
      this.uploadUrl = Deno.env.get("LLAMA_PARSE_UPLOAD_URL") ||
        "https://api.cloud.llamaindex.ai/api/parsing/upload";
      this.jobUrl = Deno.env.get("LLAMA_PARSE_JOB_URL") ||
        "https://api.cloud.llamaindex.ai/api/parsing/job";
      this.maxWaitMs = 35000;
      this.initialPollDelayMs = 2000;
      this.pollIntervalMs = 2500;
    } else {
      const opts = apiKeyOrOptions || {};
      this.apiKey = opts.apiKey || Deno.env.get("LLAMA_CLOUD_API_KEY") || "";
      this.uploadUrl = opts.uploadUrl ||
        Deno.env.get("LLAMA_PARSE_UPLOAD_URL") ||
        "https://api.cloud.llamaindex.ai/api/parsing/upload";
      this.jobUrl = opts.jobUrl ||
        Deno.env.get("LLAMA_PARSE_JOB_URL") ||
        "https://api.cloud.llamaindex.ai/api/parsing/job";
      this.maxWaitMs = opts.maxWaitMs ?? 35000;
      this.initialPollDelayMs = opts.initialPollDelayMs ?? 2000;
      this.pollIntervalMs = opts.pollIntervalMs ?? 2500;
    }

    if (!this.apiKey && !Deno.env.get("LLAMA_CLOUD_API_KEY")) {
      console.warn(
        "[LlamaParseClient] Warning: LLAMA_CLOUD_API_KEY is not set.",
      );
    }
  }

  /**
   * Uploads and parses a file using LlamaParse.
   * Handles polling and classifies rate-limiting / quota exhaustion errors.
   */
  public async parseFile(
    fileBlob: Blob,
    filename: string,
    customMaxWaitMs?: number,
  ): Promise<LlamaParseResult> {
    const key = this.apiKey || Deno.env.get("LLAMA_CLOUD_API_KEY") || "";
    if (!key) {
      return {
        success: false,
        errorType: "quota_exhausted",
        errorMessage: "Missing LLAMA_CLOUD_API_KEY in environment.",
      };
    }

    const maxWait = customMaxWaitMs ?? this.maxWaitMs;

    try {
      const formData = new FormData();
      formData.append("file", fileBlob, filename);
      formData.append("result_type", "markdown");
      formData.append("language", "en");
      formData.append("split_by_page", "true");
      formData.append("is_formatting_instruction", "true");
      formData.append(
        "formatting_instruction",
        "Extract all RFP sections, requirement matrices, RFP tables, pricing tables, deadlines, evaluation criteria, and instructions to bidders cleanly as standard Markdown tables and headings.",
      );

      // 1. Submit Upload Job
      const uploadRes = await fetch(this.uploadUrl, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${key}`,
        },
        body: formData,
      });

      // Classify immediate HTTP errors
      if (uploadRes.status === 429) {
        return {
          success: false,
          errorType: "rate_limit",
          errorMessage: "LlamaParse API rate limit exceeded (HTTP 429).",
        };
      }

      if (uploadRes.status === 402 || uploadRes.status === 403) {
        return {
          success: false,
          errorType: "quota_exhausted",
          errorMessage:
            `LlamaParse subscription/quota exhausted or forbidden (HTTP ${uploadRes.status}).`,
        };
      }

      if (!uploadRes.ok) {
        const errBody = await uploadRes.text().catch(() => "");
        return {
          success: false,
          errorType: "parsing_failed",
          errorMessage:
            `LlamaParse upload failed with HTTP ${uploadRes.status}: ${errBody}`,
        };
      }

      const uploadJson = await uploadRes.json();
      const jobId = uploadJson.id || uploadJson.job_id;

      if (!jobId) {
        return {
          success: false,
          errorType: "parsing_failed",
          errorMessage: "LlamaParse did not return a valid job ID.",
        };
      }

      // 2. Poll for Completion
      const startTime = Date.now();
      let pollInterval = this.pollIntervalMs;
      await new Promise((r) => setTimeout(r, this.initialPollDelayMs));

      while (Date.now() - startTime < maxWait) {
        const jobRes = await fetch(`${this.jobUrl}/${jobId}`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${key}`,
            Accept: "application/json",
          },
        });

        if (jobRes.status === 429) {
          return {
            success: false,
            errorType: "rate_limit",
            errorMessage: "LlamaParse polling rate limit exceeded (HTTP 429).",
            jobId,
          };
        }

        if (jobRes.status === 402 || jobRes.status === 403) {
          return {
            success: false,
            errorType: "quota_exhausted",
            errorMessage:
              `LlamaParse quota exceeded during processing (HTTP ${jobRes.status}).`,
            jobId,
          };
        }

        if (jobRes.ok) {
          const jobData = await jobRes.json();
          const status = (jobData.status || "").toUpperCase();

          if (status === "SUCCESS") {
            // 3. Fetch Result Markdown
            const resultRes = await fetch(
              `${this.jobUrl}/${jobId}/result/markdown`,
              {
                method: "GET",
                headers: {
                  Authorization: `Bearer ${key}`,
                  Accept: "application/json",
                },
              },
            );

            if (!resultRes.ok) {
              const errText = await resultRes.text().catch(() => "");
              return {
                success: false,
                errorType: "parsing_failed",
                errorMessage:
                  `Failed to fetch markdown result (HTTP ${resultRes.status}): ${errText}`,
                jobId,
              };
            }

            const resultData = await resultRes.json();
            const markdown = typeof resultData === "string"
              ? resultData
              : resultData.markdown || resultData.text || "";

            return {
              success: true,
              markdown,
              jobId,
              pagesCount: jobData.pages_count ?? jobData.num_pages,
            };
          } else if (status === "ERROR" || status === "FAILED") {
            return {
              success: false,
              errorType: "parsing_failed",
              errorMessage: jobData.error_message ||
                "LlamaParse processing job failed.",
              jobId,
            };
          }
        }

        // Wait before next poll
        await new Promise((r) => setTimeout(r, pollInterval));
        pollInterval = Math.min(pollInterval + 500, 5000);
      }

      // If we exit the loop, the job timed out
      return {
        success: false,
        errorType: "timeout",
        errorMessage: `LlamaParse processing timed out after ${
          Math.round(maxWait / 1000)
        }s.`,
        jobId,
      };
    } catch (err: unknown) {
      const error = err as Error;
      return {
        success: false,
        errorType: "parsing_failed",
        errorMessage: error.message || "LlamaParse unexpected network failure.",
      };
    }
  }
}

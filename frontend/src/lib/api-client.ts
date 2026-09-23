// ============================================================================
// RFPANDA — Direct-to-FastAPI SSE Streaming & API Client
// Completely bypasses Vercel 10s Serverless Execution Timeout
// ============================================================================

import { QueryRequest, SourceCitation, QueryDoneSummary, SystemMetrics, HealthResponse } from '@/types';

export interface StreamQueryCallbacks {
  onSources?: (sources: SourceCitation[]) => void;
  onToken?: (token: string) => void;
  onDone?: (summary: QueryDoneSummary) => void;
  onError?: (error: Error) => void;
}

export interface StreamQueryOptions extends StreamQueryCallbacks {
  backendUrl?: string;
  authToken?: string;
  signal?: AbortSignal;
}

export const DEFAULT_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  'https://rfpanda-backend.onrender.com';

/**
 * Executes a streaming RFP query directly against the FastAPI backend using SSE.
 * Bypasses Vercel serverless function limits.
 */
export async function streamRfpQuery(
  request: QueryRequest,
  options: StreamQueryOptions = {}
): Promise<{ text: string; sources: SourceCitation[]; summary?: QueryDoneSummary }> {
  const backendUrl = (options.backendUrl || DEFAULT_BACKEND_URL).replace(/\/$/, '');
  const url = `${backendUrl}/api/query`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  };

  if (options.authToken) {
    headers['Authorization'] = `Bearer ${options.authToken}`;
  }

  let accumulatedText = '';
  let extractedSources: SourceCitation[] = [];
  let doneSummary: QueryDoneSummary | undefined;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        query: request.query,
        document_ids: request.document_ids && request.document_ids.length > 0 ? request.document_ids : null,
        match_count: request.match_count ?? 5,
        similarity_threshold: request.similarity_threshold ?? 0.15,
        model: request.model ?? 'llama-3.3-70b-versatile',
      }),
      signal: options.signal,
    });

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        } else if (errorJson.error) {
          errorMessage = errorJson.error;
        }
      } catch {
        // Fallback to text error
        const text = await response.text().catch(() => '');
        if (text) errorMessage = text;
      }
      const err = new Error(errorMessage);
      options.onError?.(err);
      throw err;
    }

    if (!response.body) {
      throw new Error('Response body is null, SSE stream cannot be read.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split(/\r?\n\r?\n/);
      // Keep the last partial piece in buffer
      buffer = events.pop() || '';

      for (const rawEvent of events) {
        const trimmed = rawEvent.trim();
        if (!trimmed) continue;

        const lines = trimmed.split(/\r?\n/);
        let eventType = 'message';
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.replace(/^event:\s*/, '').trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.replace(/^data:\s*/, ''));
          }
        }

        const dataStr = dataLines.join('\n');
        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr);

          if (eventType === 'sources' || eventType === 'metadata') {
            if (Array.isArray(data.sources)) {
              extractedSources = data.sources;
              options.onSources?.(extractedSources);
            }
          } else if (eventType === 'token') {
            const tokenDelta = data.delta ?? data.text ?? '';
            if (tokenDelta) {
              accumulatedText += tokenDelta;
              options.onToken?.(tokenDelta);
            }
          } else if (eventType === 'done') {
            doneSummary = data;
            options.onDone?.(data);
          } else if (eventType === 'error') {
            const errorMsg = data.error || data.detail || 'Query streaming error';
            const errorObj = new Error(errorMsg);
            options.onError?.(errorObj);
            throw errorObj;
          }
        } catch (parseErr: any) {
          if (eventType === 'error') {
            throw parseErr;
          }
          // Non-JSON plain text fallback
          if (eventType === 'token') {
            accumulatedText += dataStr;
            options.onToken?.(dataStr);
          }
        }
      }
    }

    // Process any trailing buffer
    if (buffer.trim()) {
      const lines = buffer.trim().split(/\r?\n/);
      let eventType = 'message';
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.replace(/^event:\s*/, '').trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.replace(/^data:\s*/, ''));
        }
      }
      const dataStr = dataLines.join('\n');
      if (dataStr) {
        try {
          const data = JSON.parse(dataStr);
          if (eventType === 'token') {
            const delta = data.delta ?? data.text ?? '';
            accumulatedText += delta;
            options.onToken?.(delta);
          } else if (eventType === 'done') {
            doneSummary = data;
            options.onDone?.(data);
          }
        } catch {}
      }
    }

    return {
      text: accumulatedText,
      sources: extractedSources,
      summary: doneSummary,
    };
  } catch (err: any) {
    if (err.name === 'AbortError') {
      return {
        text: accumulatedText,
        sources: extractedSources,
        summary: doneSummary,
      };
    }
    options.onError?.(err);
    throw err;
  }
}

/**
 * Fetches free-tier memory and diagnostic metrics from the FastAPI backend.
 */
export async function fetchSystemMetrics(backendUrl?: string): Promise<SystemMetrics> {
  const base = (backendUrl || DEFAULT_BACKEND_URL).replace(/\/$/, '');
  const response = await fetch(`${base}/api/system/metrics`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!response.ok) {
    // Fallback to /health if /api/system/metrics is not available
    const healthRes = await fetch(`${base}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    if (!healthRes.ok) {
      throw new Error(`Failed to fetch system health: HTTP ${response.status}`);
    }
    const health: HealthResponse = await healthRes.json();
    return {
      memory_rss_mb: health.memory.rss_mb,
      memory_vms_mb: health.memory.vms_mb,
      cpu_percent: 0,
      threads_count: 1,
      target_limit_mb: health.memory.target_limit_mb || 300,
      within_limits: health.memory.within_limits,
      uptime_seconds: health.uptime_seconds,
    };
  }

  return await response.json();
}

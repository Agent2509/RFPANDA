// ============================================================================
// RFPANDA — Frontend Type Definitions
// ============================================================================

export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'awaiting_fallback_parse'
  | 'processed'
  | 'completed'
  | 'failed'
  | 'fallback_processing';

export interface DocumentMetadata {
  total_chunks?: number;
  total_tokens?: number;
  processed_at?: string;
  parser?: string;
  fallback_reason?: string;
  fallback_error?: string;
  fallback_timestamp?: string;
  fallback_ingested?: boolean;
  [key: string]: any;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  name: string;
  storage_path: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus;
  error_message: string | null;
  keep_forever: boolean;
  last_queried_at: string | null;
  created_at: string;
  updated_at: string;
  metadata: DocumentMetadata;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  user_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  metadata: {
    page_number?: number;
    section_header?: string;
    token_count?: number;
    file_name?: string;
    parser?: string;
    [key: string]: any;
  };
  similarity?: number;
}

export interface SourceCitation {
  chunk_id: string;
  document_id: string;
  file_name: string;
  page_number: number;
  section_header: string;
  similarity: number;
  snippet: string;
}

export interface QueryRequest {
  query: string;
  document_ids?: string[] | null;
  match_count?: number;
  similarity_threshold?: number;
  model?: string;
}

export interface QueryDoneSummary {
  finish_reason?: string;
  model?: string;
  total_sources?: number;
  completion_tokens?: number;
  total_time_ms?: number;
  prompt_tokens?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: SourceCitation[];
  timestamp: string;
  isStreaming?: boolean;
  error?: string;
  summary?: QueryDoneSummary;
}

export interface MemoryMetrics {
  rss_mb: number;
  vms_mb: number;
  percent: number;
  target_limit_mb: number;
  within_limits: boolean;
}

export interface SystemMetrics {
  memory_rss_mb: number;
  memory_vms_mb: number;
  cpu_percent: number;
  threads_count: number;
  target_limit_mb: number;
  within_limits: boolean;
  uptime_seconds: number;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  uptime_seconds: number;
  memory: MemoryMetrics;
}

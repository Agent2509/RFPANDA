// ============================================================================
// ApexTender v2.0 — Client-Side PDF.js Fallback Parser
// Extracts structured text page-by-page directly in the browser when LlamaParse
// hits rate limits, quotas, or network timeouts.
// ============================================================================

import { SupabaseClient } from '@supabase/supabase-js';

export interface ExtractedPage {
  page_number: number;
  text: string;
}

export interface ParseResult {
  fullText: string;
  pages: ExtractedPage[];
  pageCount: number;
}

export interface FallbackIngestOptions {
  onProgress?: (step: string, percent: number) => void;
  supabaseUrl?: string;
  supabaseToken?: string;
}

/**
 * Initializes and configures PDF.js in browser context.
 */
async function getPdfJs() {
  const pdfjsLib = await import('pdfjs-dist');
  if (typeof window !== 'undefined' && !pdfjsLib.GlobalWorkerOptions.workerSrc) {
    // Set standard unpkg or CDN worker fallback if local worker is not present
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version || '4.5.136'}/pdf.worker.min.mjs`;
  }
  return pdfjsLib;
}

/**
 * Extracts text from PDF bytes page by page directly in the client browser.
 */
export async function extractPdfTextFromBuffer(
  data: ArrayBuffer | Uint8Array,
  onProgress?: (percent: number, currentPage: number, totalPages: number) => void
): Promise<ParseResult> {
  const pdfjsLib = await getPdfJs();
  const loadingTask = pdfjsLib.getDocument({
    data: data instanceof Uint8Array ? data : new Uint8Array(data),
    useSystemFonts: true,
    isEvalSupported: false,
  });

  const pdfDocument = await loadingTask.promise;
  const totalPages = pdfDocument.numPages;
  const pages: ExtractedPage[] = [];
  const fullTextParts: string[] = [];

  for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
    const page = await pdfDocument.getPage(pageNum);
    const textContent = await page.getTextContent();

    // Group text items and preserve spacing/line structure
    const pageText = textContent.items
      .map((item: any) => (item && typeof item.str === 'string' ? item.str : ''))
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();

    const formattedPageHeader = `\n\n## Page ${pageNum}\n\n`;
    pages.push({
      page_number: pageNum,
      text: pageText,
    });
    fullTextParts.push(formattedPageHeader + pageText);

    const progressPct = Math.round((pageNum / totalPages) * 100);
    onProgress?.(progressPct, pageNum, totalPages);
  }

  const fullText = fullTextParts.join('\n').trim();

  return {
    fullText,
    pages,
    pageCount: totalPages,
  };
}

/**
 * Downloads a file from Supabase Storage and parses it using browser PDF.js.
 */
export async function parseDocumentFromStorage(
  storagePath: string,
  supabase: SupabaseClient,
  onProgress?: (step: string, percent: number) => void
): Promise<ParseResult> {
  onProgress?.('Downloading document from storage...', 10);

  // 1. Download file from bucket
  let fileBlob: Blob | null = null;
  const { data: rfpData, error: rfpError } = await supabase.storage
    .from('rfp-documents')
    .download(storagePath);

  if (!rfpError && rfpData) {
    fileBlob = rfpData;
  } else {
    const { data: fallbackData, error: fallbackError } = await supabase.storage
      .from('documents')
      .download(storagePath);

    if (!fallbackError && fallbackData) {
      fileBlob = fallbackData;
    } else {
      throw new Error(`Failed to download document from storage: ${rfpError?.message || fallbackError?.message}`);
    }
  }

  onProgress?.('Initializing client-side PDF parser...', 25);
  const arrayBuffer = await fileBlob.arrayBuffer();

  onProgress?.('Extracting text content...', 30);
  const result = await extractPdfTextFromBuffer(arrayBuffer, (pct) => {
    // Map 0-100 to 30-80% overall progress
    const mapped = 30 + Math.round((pct / 100) * 50);
    onProgress?.(`Parsing PDF text (${pct}%)...`, mapped);
  });

  return result;
}

/**
 * Runs full browser fallback workflow: downloads file, parses text with PDF.js,
 * and posts extracted content to the Edge Function `ingest-fallback-text`.
 */
export async function executeFallbackIngestion(
  documentId: string,
  storagePath: string,
  supabase: SupabaseClient,
  options: FallbackIngestOptions = {}
): Promise<{ status: string; total_chunks?: number; message?: string }> {
  const { onProgress } = options;

  // 1. Parse text via browser PDF.js
  const parsed = await parseDocumentFromStorage(storagePath, supabase, onProgress);

  onProgress?.('Submitting extracted text for semantic chunking & embedding...', 85);

  const supabaseUrl =
    options.supabaseUrl ||
    process.env.NEXT_PUBLIC_SUPABASE_URL ||
    'http://localhost:54321';

  // Get current auth session token
  const { data: sessionData } = await supabase.auth.getSession();
  const token = options.supabaseToken || sessionData.session?.access_token || '';

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://rfpanda-backend.onrender.com';
  const endpoint = `${backendUrl.replace(/\/$/, '')}/api/documents/fallback-parse`;

  const payload = {
    document_id: documentId,
    pages: parsed.pages,
    parser_used: 'pdfjs_client_fallback',
  };

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorJson = await response.json().catch(() => ({}));
    throw new Error(errorJson.error || errorJson.message || `Fallback ingestion failed: HTTP ${response.status}`);
  }

  const result = await response.json();
  onProgress?.('Fallback extraction complete! Document ready for querying.', 100);

  return result;
}

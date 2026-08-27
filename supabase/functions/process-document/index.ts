// ============================================================================
// ApexTender v2.0 — Supabase Edge Function: process-document
// ============================================================================

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { handleCors, jsonResponse } from "../_shared/cors.ts";
import { getServiceRoleClient } from "../_shared/supabase.ts";
import { LlamaParseClient } from "../_shared/llamaparse.ts";
import { SemanticChunker } from "../_shared/chunker.ts";
import { VoyageClient } from "../_shared/voyage.ts";

serve(async (req: Request) => {
  // Handle CORS pre-flight
  const corsRes = handleCors(req);
  if (corsRes) return corsRes;

  try {
    const supabase = getServiceRoleClient();
    const body = await req.json().catch(() => ({}));
    const documentId = body.document_id || body.id || body.record?.id;

    if (!documentId) {
      return jsonResponse(
        { error: "Missing document_id in request body" },
        400,
      );
    }

    // 1. Atomic status transition to 'processing'
    const { data: doc, error: fetchError } = await supabase
      .from("documents")
      .update({
        status: "processing",
        updated_at: new Date().toISOString(),
      })
      .eq("id", documentId)
      .in("status", [
        "uploaded",
        "awaiting_fallback_parse",
        "failed",
        "error",
        "processing",
      ])
      .select("id, user_id, name, storage_path, mime_type, metadata")
      .single();

    if (fetchError || !doc) {
      // Check if document exists and is already processed
      const { data: existingDoc } = await supabase
        .from("documents")
        .select("id, status")
        .eq("id", documentId)
        .single();

      if (existingDoc && existingDoc.status === "processed") {
        return jsonResponse({
          status: "processed",
          message: "Document has already been processed",
          document_id: documentId,
        });
      }

      return jsonResponse(
        {
          message: "Document not found or in an unprocessable state",
          document_id: documentId,
        },
        200,
      );
    }

    // 2. Download file from Supabase Storage bucket 'rfp-documents'
    const storagePath = doc.storage_path;
    let fileBlob: Blob | null = null;

    // Try 'rfp-documents' bucket first, fallback to 'documents'
    const { data: rfpData, error: rfpError } = await supabase.storage
      .from("rfp-documents")
      .download(storagePath);

    if (!rfpError && rfpData) {
      fileBlob = rfpData;
    } else {
      const { data: fallbackData, error: fallbackError } = await supabase
        .storage
        .from("documents")
        .download(storagePath);

      if (!fallbackError && fallbackData) {
        fileBlob = fallbackData;
      } else {
        const errorDetail = rfpError?.message || fallbackError?.message ||
          "File not found in storage";
        await supabase
          .from("documents")
          .update({
            status: "failed",
            error_message: `Storage download failed: ${errorDetail}`,
            updated_at: new Date().toISOString(),
          })
          .eq("id", documentId);

        return jsonResponse({
          error: `Storage download failed: ${errorDetail}`,
        }, 500);
      }
    }

    // 3. Parse Document Content
    let markdownText = "";
    const mime = (doc.mime_type || "").toLowerCase();
    const isTextDoc = mime === "text/plain" ||
      mime === "text/markdown" ||
      doc.name?.endsWith(".txt") ||
      doc.name?.endsWith(".md");

    if (isTextDoc) {
      markdownText = await fileBlob.text();
    } else {
      // Primary Parser: LlamaParse Cloud
      const llamaClient = new LlamaParseClient();
      const parseResult = await llamaClient.parseFile(
        fileBlob,
        doc.name || "document.pdf",
      );

      if (!parseResult.success) {
        console.warn(
          `[LlamaParse Primary Failed] doc_id=${documentId} errorType=${parseResult.errorType} message=${parseResult.errorMessage}`,
        );

        // Check if error qualifies for graceful client-side fallback
        const isFallbackEligible = parseResult.errorType === "rate_limit" ||
          parseResult.errorType === "quota_exhausted" ||
          parseResult.errorType === "timeout";

        if (isFallbackEligible) {
          const currentMetadata =
            (typeof doc.metadata === "object" && doc.metadata !== null)
              ? doc.metadata
              : {};
          await supabase
            .from("documents")
            .update({
              status: "awaiting_fallback_parse",
              error_message:
                `Primary parser unavailable (${parseResult.errorType}). Client-side PDF.js fallback required.`,
              metadata: {
                ...currentMetadata,
                fallback_reason: parseResult.errorType,
                fallback_error: parseResult.errorMessage,
                fallback_timestamp: new Date().toISOString(),
              },
              updated_at: new Date().toISOString(),
            })
            .eq("id", documentId);

          return jsonResponse({
            status: "awaiting_fallback_parse",
            document_id: documentId,
            error_type: parseResult.errorType,
            message:
              "Primary parser unavailable. Switched to fallback client-side parser.",
          });
        } else {
          // Unrecoverable parsing error
          await supabase
            .from("documents")
            .update({
              status: "failed",
              error_message: parseResult.errorMessage || "Parsing failed",
              updated_at: new Date().toISOString(),
            })
            .eq("id", documentId);

          return jsonResponse({
            error: parseResult.errorMessage || "Parsing failed",
          }, 500);
        }
      }

      markdownText = parseResult.markdown || "";
    }

    if (!markdownText || markdownText.trim().length === 0) {
      await supabase
        .from("documents")
        .update({
          status: "failed",
          error_message: "Document contained no extractable text.",
          updated_at: new Date().toISOString(),
        })
        .eq("id", documentId);

      return jsonResponse(
        { error: "Document contained no extractable text." },
        422,
      );
    }

    // 4. Markdown-Aware Semantic Chunking
    const chunker = new SemanticChunker({
      targetTokens: 600,
      overlapTokens: 100,
      maxTokens: 1000,
    });
    const chunks = chunker.chunkMarkdown(markdownText);

    if (chunks.length === 0) {
      await supabase
        .from("documents")
        .update({
          status: "failed",
          error_message: "Failed to generate text chunks from document.",
          updated_at: new Date().toISOString(),
        })
        .eq("id", documentId);

      return jsonResponse({ error: "Failed to generate text chunks." }, 422);
    }

    // 5. Generate Voyage AI Embeddings (voyage-3-lite, 1024d, input_type: "document")
    const voyageClient = new VoyageClient();
    const chunkTexts = chunks.map((c) => c.content);
    const { embeddings, totalTokens } = await voyageClient.embedChunks(
      chunkTexts,
      64,
    );

    if (embeddings.length !== chunks.length) {
      throw new Error(
        `Embedding count mismatch: expected ${chunks.length}, got ${embeddings.length}`,
      );
    }

    // 6. Delete old chunks if re-processing and Insert New Chunks
    await supabase.from("document_chunks").delete().eq(
      "document_id",
      documentId,
    );

    const chunkRows = chunks.map((chunk, idx) => ({
      document_id: doc.id,
      user_id: doc.user_id,
      chunk_index: chunk.chunkIndex,
      content: chunk.content,
      embedding: embeddings[idx],
      token_count: chunk.tokenCount,
      metadata: {
        ...chunk.metadata,
        parser: isTextDoc ? "plaintext" : "llamaparse",
      },
    }));

    // Batch insert 100 chunks at a time
    const DB_BATCH_SIZE = 100;
    for (let i = 0; i < chunkRows.length; i += DB_BATCH_SIZE) {
      const batch = chunkRows.slice(i, i + DB_BATCH_SIZE);
      const { error: insertErr } = await supabase.from("document_chunks")
        .insert(batch);
      if (insertErr) {
        throw new Error(`Database chunk insert error: ${insertErr.message}`);
      }
    }

    // 7. Update Document Status to 'processed'
    const docMetadata =
      (typeof doc.metadata === "object" && doc.metadata !== null)
        ? doc.metadata
        : {};
    await supabase
      .from("documents")
      .update({
        status: "processed",
        error_message: null,
        updated_at: new Date().toISOString(),
        metadata: {
          ...docMetadata,
          total_chunks: chunks.length,
          total_tokens: totalTokens,
          processed_at: new Date().toISOString(),
          parser: isTextDoc ? "plaintext" : "llamaparse",
        },
      })
      .eq("id", documentId);

    return jsonResponse({
      status: "processed",
      document_id: documentId,
      total_chunks: chunks.length,
      total_tokens: totalTokens,
      parser: isTextDoc ? "plaintext" : "llamaparse",
    });
  } catch (err: unknown) {
    const error = err as Error;
    console.error("[process-document error]", error);
    return jsonResponse(
      { error: error.message || "Internal server error" },
      500,
    );
  }
});

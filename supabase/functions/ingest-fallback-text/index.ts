// ============================================================================
// RFPANDA — Supabase Edge Function: ingest-fallback-text
// ============================================================================

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { handleCors, jsonResponse } from "../_shared/cors.ts";
import { getServiceRoleClient, getUserClient } from "../_shared/supabase.ts";
import { SemanticChunker } from "../_shared/chunker.ts";
import { VoyageClient } from "../_shared/voyage.ts";

serve(async (req: Request) => {
  // Handle CORS pre-flight
  const corsRes = handleCors(req);
  if (corsRes) return corsRes;

  try {
    const authHeader = req.headers.get("Authorization") || "";
    if (!authHeader) {
      return jsonResponse({ error: "Missing Authorization header" }, 401);
    }

    const serviceClient = getServiceRoleClient();
    const body = await req.json().catch(() => ({}));
    const documentId = body.document_id || body.id;
    const extractedText = body.text || body.extracted_text || "";
    const parserUsed = body.parser_used || "pdfjs_client_fallback";

    if (!documentId) {
      return jsonResponse(
        { error: "Missing document_id in request body" },
        400,
      );
    }

    if (!extractedText || extractedText.trim().length === 0) {
      return jsonResponse({ error: "Missing or empty extracted text" }, 400);
    }

    // Authenticate caller (verify JWT)
    let authenticatedUserId: string | null = null;
    const isServiceRole = authHeader.includes(
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "__NONE__",
    );

    if (!isServiceRole) {
      const userClient = getUserClient(authHeader);
      const {
        data: { user },
        error: userError,
      } = await userClient.auth.getUser();

      if (userError || !user) {
        return jsonResponse({ error: "Invalid or expired session token" }, 401);
      }
      authenticatedUserId = user.id;
    }

    // 1. Fetch document and verify ownership
    let docQuery = serviceClient
      .from("documents")
      .select("id, user_id, name, storage_path, status, metadata")
      .eq("id", documentId);

    if (authenticatedUserId) {
      docQuery = docQuery.eq("user_id", authenticatedUserId);
    }

    const { data: doc, error: docError } = await docQuery.single();

    if (docError || !doc) {
      return jsonResponse({ error: "Document not found or unauthorized" }, 404);
    }

    // 2. Transition status to 'processing'
    await serviceClient
      .from("documents")
      .update({
        status: "processing",
        updated_at: new Date().toISOString(),
      })
      .eq("id", documentId);

    // 3. Markdown-Aware Semantic Chunking
    const chunker = new SemanticChunker({
      targetTokens: 600,
      overlapTokens: 100,
      maxTokens: 1000,
    });
    const chunks = chunker.chunkMarkdown(extractedText);

    if (chunks.length === 0) {
      await serviceClient
        .from("documents")
        .update({
          status: "failed",
          error_message: "Fallback parser produced no valid text chunks.",
          updated_at: new Date().toISOString(),
        })
        .eq("id", documentId);

      return jsonResponse({ error: "Fallback text produced 0 chunks." }, 422);
    }

    // 4. Generate Voyage AI Embeddings (voyage-3-lite, 1024d)
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

    // 5. Clean up old chunks and insert new chunks
    await serviceClient.from("document_chunks").delete().eq(
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
        parser: parserUsed,
      },
    }));

    const DB_BATCH_SIZE = 100;
    for (let i = 0; i < chunkRows.length; i += DB_BATCH_SIZE) {
      const batch = chunkRows.slice(i, i + DB_BATCH_SIZE);
      const { error: insertErr } = await serviceClient.from("document_chunks")
        .insert(batch);
      if (insertErr) {
        throw new Error(`Database chunk insert error: ${insertErr.message}`);
      }
    }

    // 6. Update Document Status to 'processed'
    const docMetadata =
      (typeof doc.metadata === "object" && doc.metadata !== null)
        ? doc.metadata
        : {};
    await serviceClient
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
          parser: parserUsed,
          fallback_ingested: true,
        },
      })
      .eq("id", documentId);

    return jsonResponse({
      status: "processed",
      document_id: documentId,
      total_chunks: chunks.length,
      total_tokens: totalTokens,
      source: "client_fallback",
      parser: parserUsed,
    });
  } catch (err: unknown) {
    const error = err as Error;
    console.error("[ingest-fallback-text error]", error);
    return jsonResponse(
      { error: error.message || "Internal server error" },
      500,
    );
  }
});

// ============================================================================
// ApexTender v2.0 — Interactive RFP Query & Streaming Hook
// Connects directly to FastAPI backend SSE stream, bypassing Vercel timeout.
// ============================================================================

'use client';

import { useState, useCallback, useRef } from 'react';
import { ChatMessage, SourceCitation, QueryDoneSummary } from '@/types';
import { streamRfpQuery } from '@/lib/api-client';
import { getSupabaseBrowserClient } from '@/lib/supabase-client';

export function useRagQuery() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentSources, setCurrentSources] = useState<SourceCitation[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Query Settings
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [matchThreshold, setMatchThreshold] = useState<number>(0.25);
  const [topK, setTopK] = useState<number>(5);
  const [model, setModel] = useState<string>('llama-3.3-70b-versatile');

  const abortControllerRef = useRef<AbortController | null>(null);
  const supabase = getSupabaseBrowserClient();

  const sendMessage = useCallback(
    async (queryText: string) => {
      const trimmedQuery = queryText.trim();
      if (!trimmedQuery || isStreaming) return;

      setError(null);
      setCurrentSources([]);

      // Generate IDs
      const userMsgId = `user-${Date.now()}`;
      const assistantMsgId = `asst-${Date.now()}`;

      const userMessage: ChatMessage = {
        id: userMsgId,
        role: 'user',
        content: trimmedQuery,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      const initialAssistantMessage: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        let sourcesAccumulator: SourceCitation[] = [];

        await streamRfpQuery(
          {
            query: trimmedQuery,
            document_ids: selectedDocIds.length > 0 ? selectedDocIds : null,
            match_count: topK,
            similarity_threshold: matchThreshold,
            model,
          },
          {
            authToken: session?.access_token,
            signal: controller.signal,
            onSources: (sources) => {
              sourcesAccumulator = sources;
              setCurrentSources(sources);
              setMessages((prev) =>
                prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, sources } : msg))
              );
            },
            onToken: (delta) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId ? { ...msg, content: msg.content + delta } : msg
                )
              );
            },
            onDone: (summary: QueryDoneSummary) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, isStreaming: false, summary, sources: sourcesAccumulator }
                    : msg
                )
              );
            },
            onError: (err) => {
              setError(err.message);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, isStreaming: false, error: err.message }
                    : msg
                )
              );
            },
          }
        );
      } catch (err: any) {
        if (err.name === 'AbortError') {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
            )
          );
        } else {
          setError(err.message || 'Error executing query');
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? { ...msg, isStreaming: false, error: err.message || 'Stream failed' }
                : msg
            )
          );
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [isStreaming, selectedDocIds, matchThreshold, topK, model, supabase]
  );

  const abortQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentSources([]);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    currentSources,
    error,
    sendMessage,
    abortQuery,
    clearMessages,
    selectedDocIds,
    setSelectedDocIds,
    matchThreshold,
    setMatchThreshold,
    topK,
    setTopK,
    model,
    setModel,
  };
}

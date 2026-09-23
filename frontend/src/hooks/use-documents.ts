// ============================================================================
// RFPANDA — Documents Management Hook
// Handles document listing, real-time status polling, keep_forever toggle,
// deletion, and client-side fallback parsing.
// ============================================================================

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { getSupabaseBrowserClient } from '@/lib/supabase-client';
import { DocumentItem } from '@/types';
import { executeFallbackIngestion } from '@/lib/pdf-fallback';

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [parsingDocId, setParsingDocId] = useState<string | null>(null);
  const [parseProgress, setParseProgress] = useState<{ step: string; percent: number }>({
    step: '',
    percent: 0,
  });

  const supabase = getSupabaseBrowserClient();
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        setDocuments([]);
        setLoading(false);
        return;
      }

      const { data, error: fetchErr } = await supabase
        .from('documents')
        .select('*')
        .order('created_at', { ascending: false });

      if (fetchErr) throw fetchErr;

      setDocuments((data as DocumentItem[]) || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [supabase]);

  // Initial fetch and automatic polling when documents are processing
  useEffect(() => {
    fetchDocuments();

    // Check if any documents are in transition states
    const hasActiveJobs = documents.some(
      (d) => d.status === 'uploaded' || d.status === 'processing' || d.status === 'fallback_processing'
    );

    if (hasActiveJobs) {
      pollingTimerRef.current = setTimeout(() => {
        fetchDocuments();
      }, 3000);
    }

    return () => {
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
    };
  }, [fetchDocuments, documents]);

  // Toggle keep_forever flag
  const toggleKeepForever = useCallback(
    async (documentId: string, currentValue: boolean) => {
      try {
        const newValue = !currentValue;
        // Optimistic update
        setDocuments((prev) =>
          prev.map((doc) => (doc.id === documentId ? { ...doc, keep_forever: newValue } : doc))
        );

        const { error: updateErr } = await supabase
          .from('documents')
          .update({
            keep_forever: newValue,
            updated_at: new Date().toISOString(),
          })
          .eq('id', documentId);

        if (updateErr) {
          // Revert on error
          setDocuments((prev) =>
            prev.map((doc) => (doc.id === documentId ? { ...doc, keep_forever: currentValue } : doc))
          );
          throw updateErr;
        }
      } catch (err: any) {
        setError(err.message || 'Failed to update retention preference');
      }
    },
    [supabase]
  );

  // Delete document
  const deleteDocument = useCallback(
    async (documentId: string, storagePath: string) => {
      try {
        // Optimistic remove
        setDocuments((prev) => prev.filter((d) => d.id !== documentId));

        // 1. Delete storage object if present
        if (storagePath) {
          await supabase.storage.from('rfp-documents').remove([storagePath]);
          await supabase.storage.from('documents').remove([storagePath]);
        }

        // 2. Delete database record (cascades to chunks)
        const { error: delErr } = await supabase.from('documents').delete().eq('id', documentId);
        if (delErr) throw delErr;
      } catch (err: any) {
        setError(err.message || 'Failed to delete document');
        fetchDocuments();
      }
    },
    [supabase, fetchDocuments]
  );

  // Trigger fallback parser on a document
  const runFallbackParser = useCallback(
    async (documentId: string, storagePath: string) => {
      setParsingDocId(documentId);
      setParseProgress({ step: 'Starting fallback parser...', percent: 5 });

      try {
        await executeFallbackIngestion(documentId, storagePath, supabase, {
          onProgress: (step, percent) => {
            setParseProgress({ step, percent });
          },
        });
        await fetchDocuments();
      } catch (err: any) {
        setError(`Fallback parse failed: ${err.message}`);
        await fetchDocuments();
      } finally {
        setParsingDocId(null);
        setParseProgress({ step: '', percent: 0 });
      }
    },
    [supabase, fetchDocuments]
  );

  return {
    documents,
    loading,
    error,
    refreshDocuments: fetchDocuments,
    toggleKeepForever,
    deleteDocument,
    runFallbackParser,
    parsingDocId,
    parseProgress,
  };
}

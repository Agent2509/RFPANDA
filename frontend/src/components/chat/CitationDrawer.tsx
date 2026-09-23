// ============================================================================
// RFPANDA — Citation drawer
// ============================================================================

'use client';

import React from 'react';
import { SourceCitation } from '@/types';
import { Badge } from '@/components/ui';
import { X, FileText, Layers, Hash, Check, Copy } from 'lucide-react';

interface CitationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceCitation[];
}

export function CitationDrawer({ isOpen, onClose, sources }: CitationDrawerProps) {
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null);

  if (!isOpen) return null;

  const copySnippet = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end overflow-hidden bg-zinc-900/30 backdrop-blur-sm animate-fade-in">
      <div
        className="flex h-full w-full max-w-lg flex-col border-l border-zinc-200 bg-white shadow-lift animate-drawer-right"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-200/80 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-50 text-brand-600">
              <Layers className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-zinc-900">Citations</h3>
              <p className="text-xs text-zinc-400">
                {sources.length} chunk{sources.length === 1 ? '' : 's'} retrieved
              </p>
            </div>
          </div>
          <button onClick={onClose} className="icon-btn" aria-label="Close citations">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* List */}
        <div className="custom-scrollbar flex-1 space-y-3 overflow-y-auto p-5">
          {sources.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-zinc-100 text-zinc-400">
                <FileText className="h-5 w-5" />
              </span>
              <p className="mt-3 text-sm font-semibold text-zinc-700">No citations yet</p>
              <p className="mt-1 max-w-xs text-xs text-zinc-400">
                Ask a question to see the exact passages your answer is grounded in.
              </p>
            </div>
          ) : (
            sources.map((src, index) => {
              const similarityPct = Math.round(src.similarity * 100);
              return (
                <div
                  key={src.chunk_id || index}
                  className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition hover:border-brand-300"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-brand-500" />
                      <span className="truncate text-xs font-bold text-zinc-700" title={src.file_name}>
                        {src.file_name}
                      </span>
                    </div>

                    <div className="flex shrink-0 items-center gap-1.5">
                      <Badge variant="info" className="text-[10px]">p. {src.page_number || 1}</Badge>
                      <Badge
                        variant={similarityPct >= 80 ? 'success' : 'warning'}
                        className="font-mono text-[10px]"
                      >
                        {similarityPct}%
                      </Badge>
                    </div>
                  </div>

                  {src.section_header && (
                    <div className="flex items-center gap-1 rounded-lg border border-zinc-200/70 bg-zinc-50 px-2.5 py-1 text-[11px] font-medium text-zinc-500">
                      <Hash className="h-3 w-3 text-brand-500" />
                      <span className="truncate">{src.section_header}</span>
                    </div>
                  )}

                  <div className="whitespace-pre-wrap rounded-xl border border-zinc-100 bg-zinc-50/70 p-3 font-sans text-xs leading-relaxed text-zinc-600">
                    {src.snippet}
                  </div>

                  <div className="flex items-center justify-between pt-0.5 text-[11px] text-zinc-400">
                    <span className="font-mono text-[10px]">Chunk #{index + 1}</span>
                    <button
                      onClick={() => copySnippet(src.snippet, index)}
                      className="inline-flex items-center gap-1 font-medium transition hover:text-brand-600"
                    >
                      {copiedIndex === index ? (
                        <>
                          <Check className="h-3 w-3 text-emerald-600" />
                          <span className="text-emerald-600">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-zinc-200/80 px-5 py-3.5 text-xs text-zinc-400">
          <span>1024-d embeddings · pgvector</span>
          <button onClick={onClose} className="font-semibold text-brand-600 hover:text-brand-700">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

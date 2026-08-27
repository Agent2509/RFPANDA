// ============================================================================
// ApexTender v2.0 — Source Citation Drawer Component
// Slide-over panel displaying verified ground-truth chunk excerpts & similarity.
// ============================================================================

'use client';

import React from 'react';
import { SourceCitation } from '@/types';
import { Badge } from '@/components/ui';
import { X, FileText, Layers, Hash, Sparkles, ExternalLink, Check, Copy } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm flex justify-end transition-opacity animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-300"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-950 border border-emerald-800/60 flex items-center justify-center text-emerald-400">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">Ground-Truth Citations</h3>
              <p className="text-xs text-slate-400">
                {sources.length} chunk{sources.length === 1 ? '' : 's'} retrieved from pgvector
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Citations List */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
          {sources.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500 space-y-2">
              <FileText className="w-8 h-8 text-slate-600" />
              <p className="text-sm font-medium text-slate-400">No citations in current view</p>
              <p className="text-xs text-slate-600 max-w-xs">
                Submit an RFP query to view grounded vector citations and cosine similarities.
              </p>
            </div>
          ) : (
            sources.map((src, index) => {
              const similarityPct = Math.round(src.similarity * 100);
              return (
                <div
                  key={src.chunk_id || index}
                  className="p-4 rounded-xl bg-slate-850/80 border border-slate-700/80 hover:border-emerald-700/60 transition-all space-y-3"
                >
                  {/* Top Bar: Doc Name, Page, Similarity Badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 truncate">
                      <FileText className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span className="text-xs font-bold text-slate-200 truncate" title={src.file_name}>
                        {src.file_name}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Badge variant="info" className="text-[10px] py-0 px-1.5">
                        p. {src.page_number || 1}
                      </Badge>
                      <Badge
                        variant={similarityPct >= 80 ? 'success' : 'warning'}
                        className="text-[10px] py-0 px-1.5 font-mono font-bold"
                      >
                        {similarityPct}% match
                      </Badge>
                    </div>
                  </div>

                  {/* Section Header */}
                  {src.section_header && (
                    <div className="text-[11px] font-semibold text-emerald-400/90 flex items-center gap-1 bg-slate-800/60 px-2.5 py-1 rounded-md border border-slate-700/50">
                      <Hash className="w-3 h-3 text-emerald-400" />
                      <span className="truncate">{src.section_header}</span>
                    </div>
                  )}

                  {/* Snippet Content */}
                  <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 text-xs text-slate-300 font-sans leading-relaxed whitespace-pre-wrap selection:bg-emerald-900">
                    {src.snippet}
                  </div>

                  {/* Snippet Footer Action */}
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                    <span className="font-mono text-[10px]">Chunk #{index + 1}</span>
                    <button
                      onClick={() => copySnippet(src.snippet, index)}
                      className="flex items-center gap-1 text-slate-400 hover:text-emerald-400 transition-colors"
                    >
                      {copiedIndex === index ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy snippet</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 text-xs text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            1024d Voyage AI Embeddings
          </span>
          <button
            onClick={onClose}
            className="text-xs font-semibold text-emerald-400 hover:text-emerald-300"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

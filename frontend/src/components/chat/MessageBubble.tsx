// ============================================================================
// ApexTender v2.0 — Chat Message Bubble Component
// Renders markdown, code, interactive citation pills, and copy-to-clipboard.
// ============================================================================

'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { ChatMessage, SourceCitation } from '@/types';
import {
  User,
  Bot,
  Copy,
  Check,
  FileText,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
} from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
  onOpenCitation?: (sourceIndex: number) => void;
  onOpenCitationDrawer?: () => void;
}

export function MessageBubble({
  message,
  onOpenCitation,
  onOpenCitationDrawer,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isAssistant = message.role === 'assistant';

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  /**
   * Simple, secure client-side Markdown formatter for streaming answers.
   */
  const renderFormattedContent = (content: string) => {
    if (!content) return null;

    // Convert [[Doc: filename.pdf, p. X]] to markdown links for interception
    // We encode the citation data into the hash of the URL: #cite|||filename.pdf|||X
    const processedContent = content.replace(
      /\[\[Doc:\s*(.*?),\s*p\.\s*(\d+)(?:\s*-\s*.*?)?\]\]/g,
      '[Citation](#cite|||$1|||$2)'
    );

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, href, children, ...props }) => {
            if (href?.startsWith('#cite|||')) {
              const parts = href.split('|||');
              const fileName = parts[1] || 'Unknown';
              const pageNum = parts[2] || '1';
              return (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onOpenCitationDrawer?.();
                  }}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-700/60 rounded hover:bg-emerald-100 hover:text-emerald-100 transition-colors shadow-sm cursor-pointer align-middle"
                  title={`View citation in ${fileName} (p. ${pageNum})`}
                >
                  <FileText className="w-3 h-3 text-emerald-600" />
                  <span className="truncate max-w-[150px]">{fileName}</span>
                  <span className="text-emerald-600 font-mono text-[10px]">p.{pageNum}</span>
                </button>
              );
            }
            return (
              <a href={href} className="text-emerald-600 hover:underline" target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full text-sm text-left text-stone-700 border border-stone-300 rounded-2xl overflow-hidden" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => <thead className="bg-stone-100/80 text-xs uppercase text-stone-500" {...props} />,
          th: ({ node, ...props }) => <th className="px-4 py-3 border-b border-stone-300" {...props} />,
          td: ({ node, ...props }) => <td className="px-4 py-3 border-b border-stone-300/60" {...props} />,
          tr: ({ node, ...props }) => <tr className="hover:bg-stone-100/40" {...props} />,
          p: ({ node, ...props }) => <p className="leading-relaxed my-2" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc ml-6 my-2" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal ml-6 my-2" {...props} />,
          li: ({ node, ...props }) => <li className="my-1" {...props} />,
          h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-stone-800 mt-5 mb-3" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-stone-800 mt-4 mb-2" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-lg font-bold text-stone-800 mt-3 mb-1.5 text-emerald-600" {...props} />,
          h4: ({ node, ...props }) => <h4 className="text-base font-bold text-stone-800 mt-2 mb-1" {...props} />,
          blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-emerald-500/50 pl-4 py-1 my-3 bg-stone-100/30 italic text-stone-600" {...props} />,
          code: ({ node, inline, className, children, ...props }: any) => {
            return inline ? (
              <code className="bg-stone-100 text-emerald-700 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>{children}</code>
            ) : (
              <pre className="bg-white p-4 rounded-xl border border-stone-300 overflow-x-auto my-3">
                <code className="text-stone-600 text-sm font-mono" {...props}>{children}</code>
              </pre>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    );
  };

  return (
    <div
      className={`flex gap-4 p-5 rounded-2xl transition-colors ${
        isAssistant
          ? 'bg-white/90 border border-stone-200 shadow-lg'
          : 'bg-stone-50/70 border border-stone-200/60'
      }`}
    >
      {/* Avatar Icon */}
      <div
        className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md ${
          isAssistant
            ? 'bg-gradient-to-tr from-emerald-600 to-emerald-600 text-slate-950 font-bold'
            : 'bg-stone-200 text-stone-700'
        }`}
      >
        {isAssistant ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
      </div>

      {/* Message Content Body */}
      <div className="flex-1 min-w-0">
        {/* Header: Name + Timestamp + Actions */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-600">
              {isAssistant ? 'RFPanda AI (Grounded RAG)' : 'You'}
            </span>
            <span className="text-[11px] text-stone-400">{message.timestamp}</span>
          </div>

          {isAssistant && message.content && (
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1 text-xs text-stone-500 hover:text-emerald-600 px-2 py-1 rounded bg-stone-100/60 hover:bg-stone-100 border border-stone-300/60 transition-colors"
              title="Copy answer to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-600 font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}
        </div>

        {/* Error state */}
        {message.error ? (
          <div className="p-3 bg-rose-50 border border-rose-200/60 rounded-xl text-rose-700 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Generation Error</p>
              <p className="text-rose-600/90 mt-0.5">{message.error}</p>
            </div>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-stone-700">
            {renderFormattedContent(message.content)}
          </div>
        )}

        {/* Citations Footer Badge List */}
        {isAssistant && message.sources && message.sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-stone-200/80 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-stone-500 flex items-center gap-1 mr-1">
                <Layers className="w-3.5 h-3.5 text-emerald-600" />
                Retrieved Sources ({message.sources.length}):
              </span>
              {message.sources.map((src, idx) => (
                <button
                  key={src.chunk_id || idx}
                  onClick={() => {
                    onOpenCitation?.(idx);
                    onOpenCitationDrawer?.();
                  }}
                  className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 bg-stone-100 hover:bg-stone-200 text-stone-600 hover:text-emerald-700 rounded-md border border-stone-300 transition-colors"
                >
                  <FileText className="w-3 h-3 text-emerald-600" />
                  <span className="truncate max-w-[140px]">{src.file_name}</span>
                  <span className="text-emerald-600 font-mono">
                    {Math.round(src.similarity * 100)}%
                  </span>
                </button>
              ))}
            </div>

            <button
              onClick={onOpenCitationDrawer}
              className="text-xs text-emerald-600 hover:text-emerald-700 font-medium underline underline-offset-2"
            >
              View Excerpts Drawer →
            </button>
          </div>
        )}

        {/* Execution Performance Summary */}
        {isAssistant && message.summary && (
          <div className="mt-2 text-[10px] text-stone-400 font-mono flex items-center gap-2">
            <span>Model: {message.summary.model || 'openai/gpt-oss-120b'}</span>
            <span>•</span>
            <span>Tokens: {message.summary.completion_tokens || 0}</span>
            <span>•</span>
            <span>Time: {message.summary.total_time_ms ? `${message.summary.total_time_ms}ms` : '<1s'}</span>
          </div>
        )}
      </div>
    </div>
  );
}

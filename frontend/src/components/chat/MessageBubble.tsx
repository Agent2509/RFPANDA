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
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-1 text-xs font-semibold text-emerald-300 bg-emerald-950/80 border border-emerald-700/60 rounded hover:bg-emerald-900 hover:text-emerald-100 transition-colors shadow-sm cursor-pointer align-middle"
                  title={`View citation in ${fileName} (p. ${pageNum})`}
                >
                  <FileText className="w-3 h-3 text-emerald-400" />
                  <span className="truncate max-w-[150px]">{fileName}</span>
                  <span className="text-emerald-400 font-mono text-[10px]">p.{pageNum}</span>
                </button>
              );
            }
            return (
              <a href={href} className="text-emerald-400 hover:underline" target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full text-sm text-left text-slate-200 border border-slate-700 rounded-lg overflow-hidden" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => <thead className="bg-slate-800/80 text-xs uppercase text-slate-400" {...props} />,
          th: ({ node, ...props }) => <th className="px-4 py-3 border-b border-slate-700" {...props} />,
          td: ({ node, ...props }) => <td className="px-4 py-3 border-b border-slate-700/60" {...props} />,
          tr: ({ node, ...props }) => <tr className="hover:bg-slate-800/40" {...props} />,
          p: ({ node, ...props }) => <p className="leading-relaxed my-2" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc ml-6 my-2" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal ml-6 my-2" {...props} />,
          li: ({ node, ...props }) => <li className="my-1" {...props} />,
          h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-slate-100 mt-5 mb-3" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-slate-100 mt-4 mb-2" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-lg font-bold text-slate-100 mt-3 mb-1.5 text-emerald-400" {...props} />,
          h4: ({ node, ...props }) => <h4 className="text-base font-bold text-slate-100 mt-2 mb-1" {...props} />,
          blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-emerald-500/50 pl-4 py-1 my-3 bg-slate-800/30 italic text-slate-300" {...props} />,
          code: ({ node, inline, className, children, ...props }: any) => {
            return inline ? (
              <code className="bg-slate-800 text-emerald-300 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>{children}</code>
            ) : (
              <pre className="bg-slate-900 p-4 rounded-xl border border-slate-700 overflow-x-auto my-3">
                <code className="text-slate-300 text-sm font-mono" {...props}>{children}</code>
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
          ? 'bg-slate-900/90 border border-slate-800 shadow-lg'
          : 'bg-slate-850/70 border border-slate-800/60'
      }`}
    >
      {/* Avatar Icon */}
      <div
        className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md ${
          isAssistant
            ? 'bg-gradient-to-tr from-emerald-600 to-emerald-400 text-slate-950 font-bold'
            : 'bg-slate-700 text-slate-200'
        }`}
      >
        {isAssistant ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
      </div>

      {/* Message Content Body */}
      <div className="flex-1 min-w-0">
        {/* Header: Name + Timestamp + Actions */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              {isAssistant ? 'RFPanda AI (Grounded RAG)' : 'You'}
            </span>
            <span className="text-[11px] text-slate-500">{message.timestamp}</span>
          </div>

          {isAssistant && message.content && (
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-emerald-400 px-2 py-1 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 transition-colors"
              title="Copy answer to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400 font-semibold">Copied</span>
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
          <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Generation Error</p>
              <p className="text-rose-400/90 mt-0.5">{message.error}</p>
            </div>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-slate-200">
            {renderFormattedContent(message.content)}
          </div>
        )}

        {/* Citations Footer Badge List */}
        {isAssistant && message.sources && message.sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1 mr-1">
                <Layers className="w-3.5 h-3.5 text-emerald-400" />
                Retrieved Sources ({message.sources.length}):
              </span>
              {message.sources.map((src, idx) => (
                <button
                  key={src.chunk_id || idx}
                  onClick={() => {
                    onOpenCitation?.(idx);
                    onOpenCitationDrawer?.();
                  }}
                  className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-emerald-300 rounded-md border border-slate-700 transition-colors"
                >
                  <FileText className="w-3 h-3 text-emerald-400" />
                  <span className="truncate max-w-[140px]">{src.file_name}</span>
                  <span className="text-emerald-400 font-mono">
                    {Math.round(src.similarity * 100)}%
                  </span>
                </button>
              ))}
            </div>

            <button
              onClick={onOpenCitationDrawer}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium underline underline-offset-2"
            >
              View Excerpts Drawer →
            </button>
          </div>
        )}

        {/* Execution Performance Summary */}
        {isAssistant && message.summary && (
          <div className="mt-2 text-[10px] text-slate-500 font-mono flex items-center gap-2">
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

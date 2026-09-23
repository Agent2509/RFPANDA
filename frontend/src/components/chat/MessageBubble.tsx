// ============================================================================
// RFPANDA — Chat message
// ============================================================================

'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { ChatMessage } from '@/types';
import { Copy, Check, FileText, AlertCircle, Layers, Sparkles } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
  onOpenCitation?: (sourceIndex: number) => void;
  onOpenCitationDrawer?: () => void;
}

export function MessageBubble({ message, onOpenCitation, onOpenCitationDrawer }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isAssistant = message.role === 'assistant';

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const renderFormattedContent = (content: string) => {
    if (!content) return null;

    const processedContent = content.replace(
      /\[\[Doc:\s*(.*?),\s*p\.\s*(\d+)(?:\s*-\s*.*?)?\]\]/g,
      '[Citation](#cite|||$1|||$2)'
    );

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children, ...props }) => {
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
                  className="mx-0.5 inline-flex items-center gap-1 rounded-md border border-brand-200 bg-brand-50 px-1.5 py-0.5 align-middle text-[11px] font-semibold text-brand-700 transition hover:border-brand-300 hover:bg-brand-100"
                  title={`View citation in ${fileName} (p. ${pageNum})`}
                >
                  <FileText className="h-3 w-3" />
                  <span className="max-w-[150px] truncate">{fileName}</span>
                  <span className="font-mono text-[10px] text-brand-500">p.{pageNum}</span>
                </button>
              );
            }
            return (
              <a
                href={href}
                className="font-medium text-brand-600 underline underline-offset-2 hover:text-brand-700"
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            );
          },
          table: (props) => (
            <div className="my-3 overflow-x-auto rounded-xl border border-zinc-200">
              <table className="min-w-full text-left text-sm text-zinc-700" {...props} />
            </div>
          ),
          thead: (props) => <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500" {...props} />,
          th: (props) => <th className="border-b border-zinc-200 px-3 py-2 font-semibold" {...props} />,
          td: (props) => <td className="border-b border-zinc-100 px-3 py-2" {...props} />,
          p: (props) => <p className="my-2 leading-relaxed" {...props} />,
          ul: (props) => <ul className="my-2 ml-5 list-disc space-y-1 marker:text-zinc-300" {...props} />,
          ol: (props) => <ol className="my-2 ml-5 list-decimal space-y-1 marker:text-zinc-300" {...props} />,
          li: (props) => <li className="leading-relaxed" {...props} />,
          h1: (props) => <h1 className="mb-2 mt-4 text-xl font-bold text-zinc-900" {...props} />,
          h2: (props) => <h2 className="mb-2 mt-4 text-lg font-bold text-zinc-900" {...props} />,
          h3: (props) => <h3 className="mb-1.5 mt-3 text-base font-bold text-zinc-900" {...props} />,
          h4: (props) => <h4 className="mb-1 mt-2 text-sm font-bold text-zinc-900" {...props} />,
          blockquote: (props) => (
            <blockquote className="my-3 border-l-2 border-brand-300 bg-brand-50/40 px-3 py-1 text-zinc-600" {...props} />
          ),
          pre: (props) => (
            <pre className="my-3 overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900 p-3.5 text-xs" {...props} />
          ),
          code: ({ className, children, ...props }: any) => {
            const isBlock = /language-/.test(className || '') || String(children).includes('\n');
            return isBlock ? (
              <code className={`${className || ''} font-mono text-zinc-100`} {...props}>
                {children}
              </code>
            ) : (
              <code
                className="rounded-md border border-zinc-200 bg-zinc-100 px-1.5 py-0.5 font-mono text-[0.85em] text-brand-700"
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    );
  };

  /* ------------------------------------------------------------- User turn */
  if (!isAssistant) {
    return (
      <div className="flex flex-row-reverse items-start gap-3 animate-fade-up">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-zinc-200 text-xs font-bold text-zinc-600">
          You
        </span>
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  /* -------------------------------------------------------- Assistant turn */
  return (
    <div className="flex items-start gap-3 animate-fade-up">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
        <Sparkles className="h-4 w-4" />
      </span>

      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">RFPANDA</span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-zinc-300">{message.timestamp}</span>
            {message.content && (
              <button
                onClick={copyToClipboard}
                className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
                title="Copy answer"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-600" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    Copy
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {message.error ? (
          <div className="flex items-start gap-2 rounded-xl border border-rose-200/70 bg-rose-50 p-3 text-xs text-rose-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Generation error</p>
              <p className="mt-0.5 text-rose-600/90">{message.error}</p>
            </div>
          </div>
        ) : message.content ? (
          <div className="text-sm leading-relaxed text-zinc-700">{renderFormattedContent(message.content)}</div>
        ) : message.isStreaming ? (
          <div className="flex items-center gap-1.5 py-2">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        ) : null}

        {/* Citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-zinc-100 pt-3">
            <span className="mr-1 flex items-center gap-1 text-[11px] font-semibold text-zinc-400">
              <Layers className="h-3.5 w-3.5" />
              Sources
            </span>
            {message.sources.map((src, idx) => (
              <button
                key={src.chunk_id || idx}
                onClick={() => {
                  onOpenCitation?.(idx);
                  onOpenCitationDrawer?.();
                }}
                className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-600 shadow-sm transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
              >
                <FileText className="h-3 w-3 text-brand-500" />
                <span className="max-w-[130px] truncate">{src.file_name}</span>
                <span className="font-mono text-brand-500">{Math.round(src.similarity * 100)}%</span>
              </button>
            ))}
          </div>
        )}

        {/* Meta */}
        {message.summary && (
          <div className="mt-2 flex items-center gap-2 font-mono text-[10px] text-zinc-300">
            <span>{message.summary.model || 'llama-3.3-70b-versatile'}</span>
            <span>·</span>
            <span>{message.summary.completion_tokens || 0} tokens</span>
            <span>·</span>
            <span>{message.summary.total_time_ms ? `${message.summary.total_time_ms}ms` : '<1s'}</span>
          </div>
        )}
      </div>
    </div>
  );
}

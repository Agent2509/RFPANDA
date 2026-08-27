// ============================================================================
// ApexTender v2.0 — Chat Message Bubble Component
// Renders markdown, code, interactive citation pills, and copy-to-clipboard.
// ============================================================================

'use client';

import React, { useState } from 'react';
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
    if (!content && message.isStreaming) {
      return (
        <span className="inline-flex items-center gap-1.5 text-emerald-400 text-sm animate-pulse">
          <Sparkles className="w-4 h-4 animate-spin" />
          Analyzing RFP context & generating answer...
        </span>
      );
    }

    // Split lines and format paragraphs, headers, bullet points, tables, code
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];

    lines.forEach((line, index) => {
      // Inline citation tag replacer: [[Doc: filename, p. X]] or [Doc: filename, p. X]
      const renderLineWithCitations = (text: string) => {
        const citationRegex = /(\[\[?Doc:\s*([^,\]]+)(?:,\s*p\.\s*(\d+))?\]\]?)/g;
        const parts = [];
        let lastIndex = 0;
        let match;

        while ((match = citationRegex.exec(text)) !== null) {
          if (match.index > lastIndex) {
            parts.push(text.substring(lastIndex, match.index));
          }

          const rawPill = match[1];
          const fileName = match[2];
          const pageNum = match[3] || '1';

          parts.push(
            <button
              key={`citation-${match.index}`}
              onClick={(e) => {
                e.stopPropagation();
                onOpenCitationDrawer?.();
              }}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-1 text-xs font-semibold text-emerald-300 bg-emerald-950/80 border border-emerald-700/60 rounded hover:bg-emerald-900 hover:text-emerald-100 transition-colors shadow-sm"
              title={`View citation in ${fileName} (p. ${pageNum})`}
            >
              <FileText className="w-3 h-3 text-emerald-400" />
              <span>{fileName.length > 20 ? fileName.substring(0, 18) + '...' : fileName}</span>
              <span className="text-emerald-400 font-mono text-[10px]">p.{pageNum}</span>
            </button>
          );

          lastIndex = citationRegex.lastIndex;
        }

        if (lastIndex < text.length) {
          parts.push(text.substring(lastIndex));
        }

        return parts.length > 0 ? parts : text;
      };

      // Header level 3 ###
      if (line.startsWith('### ')) {
        elements.push(
          <h4 key={index} className="text-base font-bold text-slate-100 mt-3 mb-1">
            {line.replace('### ', '')}
          </h4>
        );
      }
      // Header level 2 ##
      else if (line.startsWith('## ')) {
        elements.push(
          <h3 key={index} className="text-lg font-bold text-slate-100 mt-4 mb-1.5 text-emerald-400">
            {line.replace('## ', '')}
          </h3>
        );
      }
      // Header level 1 #
      else if (line.startsWith('# ')) {
        elements.push(
          <h2 key={index} className="text-xl font-bold text-slate-100 mt-4 mb-2">
            {line.replace('# ', '')}
          </h2>
        );
      }
      // Bullet list item
      else if (line.startsWith('- ') || line.startsWith('* ')) {
        const bulletText = line.substring(2);
        elements.push(
          <li key={index} className="ml-4 list-disc text-slate-200 my-0.5">
            {renderLineWithCitations(bulletText)}
          </li>
        );
      }
      // Numbered list item
      else if (/^\d+\.\s/.test(line)) {
        const numText = line.replace(/^\d+\.\s/, '');
        elements.push(
          <li key={index} className="ml-4 list-decimal text-slate-200 my-0.5">
            {renderLineWithCitations(numText)}
          </li>
        );
      }
      // Empty line
      else if (line.trim() === '') {
        elements.push(<div key={index} className="h-2" />);
      }
      // Standard paragraph
      else {
        elements.push(
          <p key={index} className="text-slate-200 leading-relaxed my-1">
            {renderLineWithCitations(line)}
          </p>
        );
      }
    });

    return <div className="space-y-0.5">{elements}</div>;
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
            <span>Model: {message.summary.model || 'llama-3.3-70b-versatile'}</span>
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

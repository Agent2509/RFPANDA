// ============================================================================
// RFPANDA — Chat interface (SSE streaming)
// ============================================================================

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRagQuery } from '@/hooks/use-rag-query';
import { DocumentItem } from '@/types';
import { MessageBubble } from './MessageBubble';
import { CitationDrawer } from './CitationDrawer';
import { MemoryIndicator } from '@/components/system/MemoryIndicator';
import { Button } from '@/components/ui';
import {
  Send,
  Square,
  Trash2,
  Sliders,
  Sparkles,
  Bot,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ChatInterfaceProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
}

const QUICK_PROMPTS = [
  'Summarize the key points of this document.',
  'What are the most important takeaways?',
  'List all the deadlines or dates mentioned.',
  'Explain the main requirements in simple terms.',
];

export function ChatInterface({ documents, selectedDocIds }: ChatInterfaceProps) {
  const {
    messages,
    isStreaming,
    currentSources,
    sendMessage,
    abortQuery,
    clearMessages,
    matchThreshold,
    setMatchThreshold,
    topK,
    setTopK,
    model,
    setModel,
    setSelectedDocIds,
  } = useRagQuery();

  const [inputQuery, setInputQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [isCitationDrawerOpen, setIsCitationDrawerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setSelectedDocIds(selectedDocIds);
  }, [selectedDocIds, setSelectedDocIds]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [inputQuery]);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isStreaming) return;
    const query = inputQuery;
    setInputQuery('');
    sendMessage(query);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFormSubmit(e);
    }
  };

  const scopedDocNames = documents
    .filter((d) => selectedDocIds.includes(d.id))
    .map((d) => d.name);

  const hasDocuments = documents.length > 0;

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-soft">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200/80 px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
            <Bot className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h2 className="flex items-center gap-2 text-sm font-bold text-zinc-900">
              Assistant
              <span className="hidden sm:inline-flex items-center gap-1 rounded-full border border-emerald-200/70 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Grounded
              </span>
            </h2>
            <p className="truncate text-xs text-zinc-400">
              {selectedDocIds.length === 0
                ? 'Searching across all your documents'
                : `Scoped to ${selectedDocIds.length} document${selectedDocIds.length > 1 ? 's' : ''}: ${scopedDocNames.join(', ')}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <MemoryIndicator />

          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-[11px] font-semibold transition ${
              showSettings
                ? 'border-brand-200 bg-brand-50 text-brand-700'
                : 'border-zinc-200 bg-white text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800'
            }`}
            title="Retrieval parameters"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Settings</span>
            {showSettings ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>

          {currentSources.length > 0 && (
            <button
              type="button"
              onClick={() => setIsCitationDrawerOpen(true)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 px-2.5 text-[11px] font-semibold text-brand-700 transition hover:bg-brand-100/70"
            >
              <Layers className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Citations</span>
              <span className="font-mono">{currentSources.length}</span>
            </button>
          )}

          {messages.length > 0 && (
            <button onClick={clearMessages} title="Clear conversation" className="icon-btn h-8 w-8">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Settings */}
      {showSettings && (
        <div className="grid grid-cols-1 gap-5 border-b border-zinc-200/80 bg-zinc-50/70 px-4 py-4 sm:grid-cols-3 animate-fade-in">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-500">
              <span>Similarity threshold</span>
              <span className="font-mono text-brand-600">{matchThreshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.80"
              step="0.05"
              value={matchThreshold}
              onChange={(e) => setMatchThreshold(parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-brand-600"
            />
            <p className="text-[10px] text-zinc-400">Lower = broader context, higher = stricter relevance</p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-500">
              <span>Top-K chunks</span>
              <span className="font-mono text-brand-600">{topK}</span>
            </div>
            <input
              type="range"
              min="1"
              max="15"
              step="1"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full cursor-pointer accent-brand-600"
            />
            <p className="text-[10px] text-zinc-400">Number of retrieved chunks sent to the model</p>
          </div>

          <div className="space-y-2">
            <span className="block text-[11px] font-semibold text-zinc-500">Model</span>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="field py-2 text-xs">
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B · Versatile</option>
              <option value="llama-3.1-8b-instant">Llama 3.1 8B · Instant</option>
            </select>
            <p className="text-[10px] text-zinc-400">Inference via Groq</p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="custom-scrollbar flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
        {messages.length === 0 ? (
          <div className="mx-auto flex max-w-xl flex-col items-center justify-center py-10 text-center animate-fade-up">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-card">
              <Sparkles className="h-6 w-6" />
            </span>
            <h3 className="mt-4 text-lg font-bold tracking-tight text-zinc-900">
              Ask anything about your documents
            </h3>
            <p className="mt-1 max-w-sm text-sm text-zinc-400">
              Every answer is grounded in your uploads with page-level citations.
            </p>

            <div className="mt-6 w-full text-left">
              <span className="eyebrow">Try asking</span>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    disabled={!hasDocuments}
                    className="group flex items-start gap-2 rounded-xl border border-zinc-200 bg-white p-3 text-left text-xs text-zinc-600 shadow-sm transition hover:border-brand-300 hover:bg-brand-50/40 hover:text-zinc-900 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span className="mt-0.5 font-bold text-brand-500 transition group-hover:translate-x-0.5">→</span>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onOpenCitationDrawer={() => setIsCitationDrawerOpen(true)}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Composer */}
      <div className="border-t border-zinc-200/80 bg-white p-3 sm:p-4">
        <form
          onSubmit={handleFormSubmit}
          className="relative rounded-2xl border border-zinc-200 bg-zinc-50/70 p-1.5 transition focus-within:border-brand-400 focus-within:ring-4 focus-within:ring-brand-500/10"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              !hasDocuments
                ? 'Upload a document to start asking questions…'
                : 'Ask a question about your documents…'
            }
            disabled={!hasDocuments || isStreaming}
            className="max-h-40 w-full resize-none bg-transparent px-3 py-2.5 pr-24 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none disabled:opacity-50"
          />

          <div className="absolute bottom-2 right-2 flex items-center gap-2">
            {isStreaming ? (
              <Button type="button" variant="danger" size="sm" onClick={abortQuery} className="gap-1.5">
                <Square className="h-3 w-3 fill-current" />
                Stop
              </Button>
            ) : (
              <Button
                type="submit"
                size="sm"
                disabled={!inputQuery.trim() || !hasDocuments}
                className="gap-1.5"
              >
                Ask
                <Send className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </form>

        <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-zinc-400">
          <span>
            <kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 font-sans">Enter</kbd> to send ·{' '}
            <kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 font-sans">Shift</kbd>+
            <kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 font-sans">Enter</kbd> for new line
          </span>
          <span className="hidden items-center gap-1.5 sm:flex">
            <span className={`h-1.5 w-1.5 rounded-full ${isStreaming ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            {isStreaming ? 'Streaming…' : 'Ready'}
          </span>
        </div>
      </div>

      <CitationDrawer
        isOpen={isCitationDrawerOpen}
        onClose={() => setIsCitationDrawerOpen(false)}
        sources={currentSources}
      />
    </div>
  );
}

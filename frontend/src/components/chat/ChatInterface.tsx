// ============================================================================
// ApexTender v2.0 — Interactive RFP Query & Streaming Chat Interface
// Connects directly to FastAPI SSE backend, bypassing Vercel's 10s timeout.
// ============================================================================

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRagQuery } from '@/hooks/use-rag-query';
import { DocumentItem } from '@/types';
import { MessageBubble } from './MessageBubble';
import { CitationDrawer } from './CitationDrawer';
import { Button } from '@/components/ui';
import {
  Send,
  Square,
  Trash2,
  Sliders,
  Sparkles,
  Bot,
  Layers,
  HelpCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ChatInterfaceProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
}

const QUICK_PROMPTS = [
  'What are the SLA penalty terms and uptime guarantees?',
  'Summarize data security, encryption & GDPR compliance requirements.',
  'List all mandatory pricing schedules and payment milestones.',
  'Identify required technical certifications and vendor qualifications.',
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

  // Sync selectedDocIds from parent DocumentList
  useEffect(() => {
    setSelectedDocIds(selectedDocIds);
  }, [selectedDocIds, setSelectedDocIds]);

  // Autoscroll on new messages/tokens
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

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

  // Find names of currently scoped documents
  const scopedDocNames = documents
    .filter((d) => selectedDocIds.includes(d.id))
    .map((d) => d.name);

  return (
    <div className="flex flex-col h-full bg-slate-900/60 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-sm overflow-hidden">
      {/* Top Header Bar */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-600 to-emerald-400 flex items-center justify-center text-slate-950 font-bold shadow-md shadow-emerald-500/20">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              RFP Assistant
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60 font-mono font-medium">
                SSE Direct Stream
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              {selectedDocIds.length === 0
                ? 'Grounded search across all tenant RFP documents'
                : `Scoped to ${selectedDocIds.length} document${selectedDocIds.length > 1 ? 's' : ''}: ${scopedDocNames.join(', ')}`}
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 rounded-lg border text-xs flex items-center gap-1.5 transition-colors ${
              showSettings
                ? 'bg-emerald-950 border-emerald-700 text-emerald-300'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white'
            }`}
            title="Adjust RAG parameters (similarity threshold, top-k, model)"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span className="hidden sm:inline font-medium">RAG Parameters</span>
            {showSettings ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {currentSources.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsCitationDrawerOpen(true)}
              className="text-xs py-1.5 px-3 flex items-center gap-1.5 border-emerald-800/60 text-emerald-300 bg-emerald-950/40 hover:bg-emerald-900/60"
            >
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <span>Citations ({currentSources.length})</span>
            </Button>
          )}

          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              title="Clear conversation"
              className="p-2 rounded-lg border border-slate-700 bg-slate-800/80 text-slate-400 hover:text-rose-400 hover:border-rose-800 hover:bg-rose-950/40 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Expandable Query Settings Drawer */}
      {showSettings && (
        <div className="p-4 bg-slate-850 border-b border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs animate-in slide-in-from-top-2 duration-200">
          {/* Similarity Threshold */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-slate-300 font-semibold">
              <span>Similarity Threshold:</span>
              <span className="text-emerald-400 font-mono font-bold">{matchThreshold}</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.80"
              step="0.05"
              value={matchThreshold}
              onChange={(e) => setMatchThreshold(parseFloat(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <p className="text-[10px] text-slate-500">Lower = broader context; Higher = strict relevance</p>
          </div>

          {/* Top-K Chunks */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-slate-300 font-semibold">
              <span>Top-K Context Chunks:</span>
              <span className="text-emerald-400 font-mono font-bold">{topK}</span>
            </div>
            <input
              type="range"
              min="1"
              max="15"
              step="1"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <p className="text-[10px] text-slate-500">Number of retrieved chunks sent to Groq LLM</p>
          </div>

          {/* Model Switcher */}
          <div className="space-y-1.5">
            <span className="block text-slate-300 font-semibold">Groq Model:</span>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-lg p-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B (High Reasoning)</option>
              <option value="llama-3.1-8b-instant">Llama 3.1 8B (Sub-Second Fast)</option>
            </select>
            <p className="text-[10px] text-slate-500">Fast inference via Groq LPUs</p>
          </div>
        </div>
      )}

      {/* Chat Messages Flow Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center max-w-xl mx-auto space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-slate-800 border border-slate-700/80 flex items-center justify-center text-emerald-400 shadow-xl shadow-emerald-950/20">
              <Sparkles className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-100">Ask Anything About Your RFPs</h3>
              <p className="text-xs text-slate-400 mt-1">
                RFPanda performs high-precision semantic search over your uploaded proposal documents and streams grounded answers with page-level citations.
              </p>
            </div>

            {/* Quick Prompt Suggestions */}
            <div className="w-full text-left pt-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                Suggested Analyst Queries:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    className="text-left p-3 rounded-xl bg-slate-850/80 hover:bg-slate-800 border border-slate-700/70 hover:border-emerald-600/60 text-xs text-slate-300 hover:text-slate-100 transition-all shadow-sm group"
                  >
                    <span className="text-emerald-400 group-hover:text-emerald-300 mr-1.5 font-bold">→</span>
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

      {/* Input Area Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/95">
        <form onSubmit={handleFormSubmit} className="relative">
          <textarea
            ref={textareaRef}
            rows={2}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              documents.length === 0
                ? 'Upload an RFP document above to enable querying...'
                : 'Ask a specific question about clauses, pricing, SLAs, or technical specs (Enter to submit)...'
            }
            disabled={documents.length === 0 || isStreaming}
            className="w-full p-3.5 pr-28 bg-slate-800/80 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none transition-all disabled:opacity-50"
          />

          <div className="absolute right-3 bottom-3.5 flex items-center gap-2">
            {isStreaming ? (
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={abortQuery}
                className="py-1.5 px-3 text-xs flex items-center gap-1.5"
              >
                <Square className="w-3 h-3 fill-current" />
                Stop
              </Button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={!inputQuery.trim() || documents.length === 0}
                className="py-1.5 px-3.5 text-xs flex items-center gap-1.5"
              >
                <span>Ask</span>
                <Send className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </form>

        <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 px-1">
          <span>Press Enter to send • Shift+Enter for new line</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Direct SSE Stream (&lt;100ms TTFT)
          </span>
        </div>
      </div>

      {/* Ground-Truth Citation Drawer */}
      <CitationDrawer
        isOpen={isCitationDrawerOpen}
        onClose={() => setIsCitationDrawerOpen(false)}
        sources={currentSources}
      />
    </div>
  );
}

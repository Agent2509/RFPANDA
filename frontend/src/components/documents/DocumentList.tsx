// ============================================================================
// RFPANDA — Document Library
// ============================================================================

'use client';

import React, { useState } from 'react';
import { DocumentItem } from '@/types';
import { DocumentCard } from './DocumentCard';
import { ProgressBar } from '@/components/ui';
import {
  Search,
  RefreshCw,
  CheckSquare,
  Square,
  FileQuestion,
  Loader2,
  Sparkles,
} from 'lucide-react';

interface DocumentListProps {
  documents: DocumentItem[];
  loading: boolean;
  selectedDocIds: string[];
  onSelectDocIds: (ids: string[]) => void;
  onToggleKeepForever: (id: string, currentValue: boolean) => void;
  onDelete: (id: string, storagePath: string) => void;
  onRefresh: () => void;
  onRunFallback: (id: string, storagePath: string) => void;
  parsingDocId: string | null;
  parseProgress: { step: string; percent: number };
}

export function DocumentList({
  documents,
  loading,
  selectedDocIds,
  onSelectDocIds,
  onToggleKeepForever,
  onDelete,
  onRefresh,
  onRunFallback,
  parsingDocId,
  parseProgress,
}: DocumentListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredDocuments = documents.filter((doc) =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const readyDocuments = documents.filter(
    (doc) => doc.status === 'processed' || doc.status === 'completed'
  );

  const allSelected =
    readyDocuments.length > 0 && selectedDocIds.length === readyDocuments.length;

  const handleToggleSelect = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      onSelectDocIds(selectedDocIds.filter((id) => id !== docId));
    } else {
      onSelectDocIds([...selectedDocIds, docId]);
    }
  };

  const handleSelectAll = () => {
    if (allSelected) {
      onSelectDocIds([]);
    } else {
      onSelectDocIds(readyDocuments.map((d) => d.id));
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold tracking-tight text-zinc-900">Library</h3>
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-semibold text-zinc-500">
            {documents.length}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {readyDocuments.length > 0 && (
            <button
              onClick={handleSelectAll}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] font-semibold text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800"
              title={allSelected ? 'Deselect all' : 'Select all ready documents'}
            >
              {allSelected ? (
                <CheckSquare className="h-3.5 w-3.5 text-brand-600" />
              ) : (
                <Square className="h-3.5 w-3.5" />
              )}
              {allSelected ? `All (${selectedDocIds.length})` : `Scope (${selectedDocIds.length}/${readyDocuments.length})`}
            </button>
          )}

          <button
            onClick={onRefresh}
            className="icon-btn h-7 w-7"
            title="Refresh statuses"
            aria-label="Refresh document statuses"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-brand-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mt-3">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search documents..."
          className="field field-icon py-2 text-xs"
        />
      </div>

      {/* Parsing banner */}
      {parsingDocId && (
        <div className="mt-3 rounded-xl border border-amber-200/70 bg-amber-50 p-3 animate-fade-in">
          <div className="flex items-center justify-between text-[11px] font-semibold text-amber-800">
            <span className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 animate-spin text-amber-600" />
              {parseProgress.step || 'Parsing in browser...'}
            </span>
            <span className="font-mono">{parseProgress.percent}%</span>
          </div>
          <ProgressBar value={parseProgress.percent} className="mt-2 h-1" barClassName="bg-amber-500" />
        </div>
      )}

      {/* Items */}
      <div className="custom-scrollbar -mx-1 mt-3 flex-1 space-y-2.5 overflow-y-auto px-1 pb-1">
        {loading && documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-zinc-400">
            <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
            <p className="text-xs font-medium">Loading library…</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-4 py-16 text-center">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-zinc-100 text-zinc-400">
              <FileQuestion className="h-5 w-5" />
            </span>
            <p className="mt-3 text-sm font-semibold text-zinc-700">
              {searchQuery ? 'No matches' : 'No documents yet'}
            </p>
            <p className="mt-1 max-w-[220px] text-xs text-zinc-400">
              {searchQuery
                ? 'Try a different search term.'
                : 'Upload a PDF, DOCX, TXT, or Markdown file to start asking questions.'}
            </p>
          </div>
        ) : (
          filteredDocuments.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              isSelected={selectedDocIds.includes(doc.id)}
              onToggleSelect={handleToggleSelect}
              onToggleKeepForever={onToggleKeepForever}
              onDelete={onDelete}
              onRunFallback={onRunFallback}
              isParsingFallback={parsingDocId === doc.id}
            />
          ))
        )}
      </div>

      {/* Footer */}
      {documents.length > 0 && (
        <div className="mt-2 flex items-center justify-between border-t border-zinc-200/80 pt-2.5 text-[11px] text-zinc-400">
          <span>
            {selectedDocIds.length === 0
              ? 'Scope: all documents'
              : `Scope: ${selectedDocIds.length} selected`}
          </span>
          <span className="font-medium">
            {readyDocuments.length} ready / {documents.length}
          </span>
        </div>
      )}
    </div>
  );
}

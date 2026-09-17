// ============================================================================
// ApexTender v2.0 — Document List & Library Component
// ============================================================================

'use client';

import React, { useState } from 'react';
import { DocumentItem } from '@/types';
import { DocumentCard } from './DocumentCard';
import { Button } from '@/components/ui';
import {
  FolderArchive,
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

  const handleToggleSelect = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      onSelectDocIds(selectedDocIds.filter((id) => id !== docId));
    } else {
      onSelectDocIds([...selectedDocIds, docId]);
    }
  };

  const handleSelectAll = () => {
    if (selectedDocIds.length === readyDocuments.length) {
      onSelectDocIds([]);
    } else {
      onSelectDocIds(readyDocuments.map((d) => d.id));
    }
  };

  return (
    <div className="w-full flex flex-col h-full bg-white/60 border border-stone-200 rounded-2xl shadow-lg backdrop-blur-sm overflow-hidden">
      {/* Header & Controls */}
      <div className="p-4 border-b border-stone-200 bg-white/90 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderArchive className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-stone-800 uppercase tracking-wider">
              Document Library
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 font-semibold">
              {documents.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {readyDocuments.length > 0 && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handleSelectAll}
                className="text-xs py-1 px-2 text-stone-600 hover:text-stone-900 flex items-center gap-1"
                title={selectedDocIds.length === readyDocuments.length ? 'Deselect all' : 'Select all ready documents'}
              >
                {selectedDocIds.length === readyDocuments.length && readyDocuments.length > 0 ? (
                  <>
                    <CheckSquare className="w-3.5 h-3.5 text-emerald-600" />
                    All ({selectedDocIds.length})
                  </>
                ) : (
                  <>
                    <Square className="w-3.5 h-3.5 text-stone-400" />
                    Scope ({selectedDocIds.length}/{readyDocuments.length})
                  </>
                )}
              </Button>
            )}

            <button
              onClick={onRefresh}
              title="Refresh document statuses"
              className="p-1.5 rounded-full border border-stone-300 bg-stone-100/60 text-stone-500 hover:text-stone-700 hover:bg-stone-200 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by title..."
            className="w-full pl-9 pr-3 py-1.5 bg-stone-100/60 border border-stone-300/80 rounded-2xl text-stone-700 placeholder-stone-400 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>

      {/* Fallback Parsing Active Banner */}
      {parsingDocId && (
        <div className="p-3 bg-amber-50 border-b border-amber-200/60 text-amber-200 text-xs space-y-2">
          <div className="flex items-center justify-between font-semibold">
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-600 animate-spin" />
              {parseProgress.step || 'Running client-side PDF parser...'}
            </span>
            <span>{parseProgress.percent}%</span>
          </div>
          <div className="w-full bg-white rounded-full h-1 overflow-hidden">
            <div
              className="bg-amber-400 h-1 transition-all duration-200 rounded-full"
              style={{ width: `${parseProgress.percent}%` }}
            />
          </div>
        </div>
      )}

      {/* Document Items List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
        {loading && documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-stone-400 space-y-2">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
            <p className="text-xs">Loading document repository...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center p-4">
            <div className="w-10 h-10 rounded-full bg-stone-100/80 flex items-center justify-center text-stone-400 mb-2">
              <FileQuestion className="w-5 h-5" />
            </div>
            <p className="text-sm font-semibold text-stone-600">
              {searchQuery ? 'No matching documents' : 'No documents uploaded yet'}
            </p>
            <p className="text-xs text-stone-400 mt-1 max-w-[200px]">
              {searchQuery
                ? 'Try adjusting your search keywords.'
                : 'Upload your first RFP document above to begin asking questions.'}
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

      {/* Footer summary */}
      {documents.length > 0 && (
        <div className="p-2.5 px-4 bg-[#FAFAF8]/60 border-t border-stone-200 text-[11px] text-stone-500 flex items-center justify-between">
          <span>
            {selectedDocIds.length === 0
              ? 'Query scope: All tenant documents'
              : `Query scope: ${selectedDocIds.length} selected document${selectedDocIds.length > 1 ? 's' : ''}`}
          </span>
          <span className="text-stone-400">
            {readyDocuments.length} ready / {documents.length} total
          </span>
        </div>
      )}
    </div>
  );
}

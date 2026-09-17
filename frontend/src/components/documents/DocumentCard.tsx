// ============================================================================
// ApexTender v2.0 — Document Card Component
// Displays document metadata, status, keep_forever toggle, and fallback action.
// ============================================================================

'use client';

import React from 'react';
import { DocumentItem } from '@/types';
import { Badge, Button } from '@/components/ui';
import {
  FileText,
  Trash2,
  Lock,
  Unlock,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  Layers,
  Sparkles,
  ExternalLink,
} from 'lucide-react';

interface DocumentCardProps {
  document: DocumentItem;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onToggleKeepForever: (id: string, currentValue: boolean) => void;
  onDelete: (id: string, storagePath: string) => void;
  onRunFallback: (id: string, storagePath: string) => void;
  isParsingFallback?: boolean;
}

export function DocumentCard({
  document,
  isSelected,
  onToggleSelect,
  onToggleKeepForever,
  onDelete,
  onRunFallback,
  isParsingFallback,
}: DocumentCardProps) {
  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatRelativeTime = (isoString?: string | null) => {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const renderStatusBadge = () => {
    switch (document.status) {
      case 'processed':
      case 'completed':
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Ready
          </Badge>
        );
      case 'processing':
      case 'fallback_processing':
        return (
          <Badge variant="warning" className="gap-1 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin text-amber-600" />
            Embedding...
          </Badge>
        );
      case 'uploaded':
        return (
          <Badge variant="info" className="gap-1">
            <Clock className="w-3 h-3 text-sky-600" />
            Queued
          </Badge>
        );
      case 'awaiting_fallback_parse':
        return (
          <Badge variant="warning" className="gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Fallback Ready
          </Badge>
        );
      case 'failed':
      default:
        return (
          <Badge variant="error" className="gap-1">
            <AlertTriangle className="w-3 h-3 text-rose-600" />
            Failed
          </Badge>
        );
    }
  };

  const totalChunks = document.metadata?.total_chunks ?? 0;

  return (
    <div
      className={`relative p-4 rounded-xl border transition-all duration-200 ${
        isSelected
          ? 'bg-emerald-50 border-emerald-500/70 shadow-md shadow-emerald-50'
          : 'bg-white/80 border-stone-200 hover:border-stone-300/80 hover:bg-stone-50/50'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Document Selection Checkbox & Icon */}
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(document.id)}
            disabled={document.status !== 'processed' && document.status !== 'completed'}
            className="mt-1 w-4 h-4 rounded text-emerald-600 bg-stone-100 border-stone-300 focus:ring-emerald-500 focus:ring-offset-white cursor-pointer disabled:opacity-30"
          />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-semibold text-stone-800 truncate max-w-[220px]" title={document.name}>
                {document.name}
              </h4>
              {renderStatusBadge()}
            </div>

            {/* Subtitle / File Metadata */}
            <div className="flex items-center gap-3 mt-1.5 text-xs text-stone-500">
              <span>{formatBytes(document.file_size)}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Layers className="w-3 h-3 text-stone-400" />
                {totalChunks > 0 ? `${totalChunks} chunks` : '0 chunks'}
              </span>
              <span>•</span>
              <span title={`Last queried: ${document.last_queried_at || 'Never'}`}>
                Queried: {formatRelativeTime(document.last_queried_at)}
              </span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Keep Forever Toggle Switch */}
          <button
            type="button"
            onClick={() => onToggleKeepForever(document.id, document.keep_forever)}
            title={
              document.keep_forever
                ? 'Protected from 30-day auto-cleanup (Click to disable)'
                : 'Subject to 30-day stale auto-cleanup (Click to keep forever)'
            }
            className={`p-1.5 rounded-full border transition-colors ${
              document.keep_forever
                ? 'bg-emerald-50 border-emerald-700 text-emerald-700 hover:bg-emerald-100/60'
                : 'bg-stone-100/60 border-stone-300 text-stone-500 hover:text-stone-700'
            }`}
          >
            {document.keep_forever ? (
              <Lock className="w-3.5 h-3.5" />
            ) : (
              <Unlock className="w-3.5 h-3.5" />
            )}
          </button>

          {/* Delete Button */}
          <button
            type="button"
            onClick={() => {
              if (confirm(`Delete document "${document.name}"? This action is permanent.`)) {
                onDelete(document.id, document.storage_path);
              }
            }}
            title="Delete document"
            className="p-1.5 rounded-full border border-stone-300 bg-stone-100/60 text-stone-500 hover:text-rose-600 hover:border-rose-200/60 hover:bg-rose-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Special Fallback Parse Action Banner */}
      {document.status === 'awaiting_fallback_parse' && (
        <div className="mt-3 p-2.5 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-between gap-2">
          <div className="text-xs text-amber-700">
            <span className="font-semibold">LlamaParse rate limit reached.</span> Extract text via browser PDF.js engine?
          </div>
          <Button
            size="sm"
            variant="primary"
            disabled={isParsingFallback}
            isLoading={isParsingFallback}
            onClick={() => onRunFallback(document.id, document.storage_path)}
            className="text-xs py-1 px-2.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold flex-shrink-0"
          >
            <Sparkles className="w-3 h-3 mr-1" />
            Run Fallback
          </Button>
        </div>
      )}

      {/* Error Message Details */}
      {document.status === 'failed' && document.error_message && (
        <div className="mt-2 text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-100/40 truncate" title={document.error_message}>
          {document.error_message}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// RFPANDA — Document Card
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
    const diffMs = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diffMs / 60000);
    const hours = Math.floor(mins / 60);
    const days = Math.floor(hours / 24);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  const isReady = document.status === 'processed' || document.status === 'completed';

  const renderStatusBadge = () => {
    switch (document.status) {
      case 'processed':
      case 'completed':
        return (
          <Badge variant="success">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </Badge>
        );
      case 'processing':
      case 'fallback_processing':
        return (
          <Badge variant="warning" className="animate-pulse">
            <Loader2 className="h-3 w-3 animate-spin" />
            Embedding
          </Badge>
        );
      case 'uploaded':
        return (
          <Badge variant="info">
            <Clock className="h-3 w-3" />
            Queued
          </Badge>
        );
      case 'awaiting_fallback_parse':
        return (
          <Badge variant="warning">
            <AlertTriangle className="h-3 w-3" />
            Fallback ready
          </Badge>
        );
      case 'failed':
      default:
        return (
          <Badge variant="error">
            <AlertTriangle className="h-3 w-3" />
            Failed
          </Badge>
        );
    }
  };

  const totalChunks = document.metadata?.total_chunks ?? 0;

  return (
    <div
      className={`group rounded-xl border p-3 transition-all ${
        isSelected
          ? 'border-brand-300 bg-brand-50/60 ring-1 ring-brand-200'
          : 'border-zinc-200/80 bg-white hover:border-zinc-300 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start gap-2.5">
        {/* Selection */}
        <button
          type="button"
          onClick={() => isReady && onToggleSelect(document.id)}
          disabled={!isReady}
          aria-label={isSelected ? 'Deselect document' : 'Select document'}
          className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border transition ${
            isSelected
              ? 'border-brand-600 bg-brand-600 text-white'
              : 'border-zinc-300 bg-white text-transparent hover:border-zinc-400'
          } ${!isReady ? 'cursor-not-allowed opacity-30' : ''}`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
        </button>

        {/* Body */}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-zinc-100 text-zinc-500 group-hover:bg-brand-50 group-hover:text-brand-600 transition-colors">
                <FileText className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-zinc-800" title={document.name}>
                  {document.name}
                </p>
                <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-zinc-400">
                  <span>{formatBytes(document.file_size)}</span>
                  <span>·</span>
                  <span className="flex items-center gap-1">
                    <Layers className="h-3 w-3" />
                    {totalChunks > 0 ? `${totalChunks} chunks` : 'no chunks'}
                  </span>
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 max-lg:opacity-100">
              <button
                type="button"
                onClick={() => onToggleKeepForever(document.id, document.keep_forever)}
                title={document.keep_forever ? 'Protected from auto-cleanup' : 'Keep forever (skip auto-cleanup)'}
                className={`icon-btn h-7 w-7 ${document.keep_forever ? 'border-brand-200 bg-brand-50 text-brand-600' : ''}`}
              >
                {document.keep_forever ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`Delete "${document.name}"? This cannot be undone.`)) {
                    onDelete(document.id, document.storage_path);
                  }
                }}
                title="Delete document"
                className="icon-btn icon-btn-danger h-7 w-7"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between gap-2">
            {renderStatusBadge()}
            <span className="text-[10px] text-zinc-400" title={document.last_queried_at || 'Never queried'}>
              queried {formatRelativeTime(document.last_queried_at)}
            </span>
          </div>

          {/* Fallback action */}
          {document.status === 'awaiting_fallback_parse' && (
            <div className="mt-2.5 flex items-center justify-between gap-2 rounded-lg border border-amber-200/70 bg-amber-50 p-2">
              <p className="text-[11px] leading-tight text-amber-800">
                Primary parser hit a rate limit. Extract locally?
              </p>
              <Button
                size="sm"
                onClick={() => onRunFallback(document.id, document.storage_path)}
                disabled={isParsingFallback}
                isLoading={isParsingFallback}
                className="shrink-0 bg-amber-500 text-amber-950 hover:bg-amber-400"
              >
                {!isParsingFallback && <Sparkles className="h-3 w-3" />}
                Run fallback
              </Button>
            </div>
          )}

          {/* Error */}
          {document.status === 'failed' && document.error_message && (
            <p
              className="mt-2 truncate rounded-lg border border-rose-100 bg-rose-50 px-2 py-1.5 text-[11px] text-rose-600"
              title={document.error_message}
            >
              {document.error_message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

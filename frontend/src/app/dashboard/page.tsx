// ============================================================================
// RFPANDA — Workspace
// Two-pane layout: document library rail + grounded RAG chat.
// ============================================================================

'use client';

import React, { useState } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { useDocuments } from '@/hooks/use-documents';
import { UploadDropzone } from '@/components/upload/UploadDropzone';
import { DocumentList } from '@/components/documents/DocumentList';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { MemoryIndicator } from '@/components/system/MemoryIndicator';
import { Button } from '@/components/ui';
import { LogOut, LogIn, Menu, X, PanelLeft } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { user, loading: authLoading, signOut } = useAuth();
  const {
    documents,
    loading: docsLoading,
    refreshDocuments,
    toggleKeepForever,
    deleteDocument,
    runFallbackParser,
    parsingDocId,
    parseProgress,
  } = useDocuments();

  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [railCollapsed, setRailCollapsed] = useState(false);

  const Sidebar = (
    <div className="flex h-full flex-col">
      {/* Brand */}
      <div className="flex items-center justify-between px-4 h-16 border-b border-zinc-200/80">
        <Link href="/" className="flex items-center gap-2.5 group">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-zinc-900 text-lg shadow-sm transition group-hover:scale-105">
            🐼
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-sm font-extrabold tracking-tight text-zinc-900">RFPANDA</span>
            <span className="text-[10px] font-medium text-zinc-400">Document AI</span>
          </span>
        </Link>

        <button
          onClick={() => setMobileNavOpen(false)}
          className="icon-btn lg:hidden"
          aria-label="Close navigation"
        >
          <X className="h-4 w-4" />
        </button>
        <button
          onClick={() => setRailCollapsed(true)}
          className="icon-btn hidden lg:inline-flex"
          aria-label="Collapse library"
          title="Collapse library"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      </div>

      {/* Upload */}
      <div className="px-4 pt-4">
        <UploadDropzone onUploadSuccess={refreshDocuments} />
      </div>

      {/* Library */}
      <div className="flex-1 min-h-0 px-4 py-4">
        <DocumentList
          documents={documents}
          loading={docsLoading}
          selectedDocIds={selectedDocIds}
          onSelectDocIds={setSelectedDocIds}
          onToggleKeepForever={toggleKeepForever}
          onDelete={deleteDocument}
          onRefresh={refreshDocuments}
          onRunFallback={runFallbackParser}
          parsingDocId={parsingDocId}
          parseProgress={parseProgress}
        />
      </div>

      {/* Account footer */}
      <div className="border-t border-zinc-200/80 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white">
              {user?.email ? user.email.charAt(0).toUpperCase() : '?'}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-xs font-semibold text-zinc-700">
                {user?.email || 'Guest'}
              </span>
              <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-600">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Signed in
              </span>
            </span>
          </div>

          {!authLoading && user ? (
            <button onClick={signOut} className="icon-btn icon-btn-danger" title="Sign out" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          ) : !authLoading ? (
            <Link href="/login">
              <Button size="sm" className="gap-1.5">
                <LogIn className="h-3.5 w-3.5" />
                Sign in
              </Button>
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-full overflow-hidden bg-canvas">
      {/* Desktop library rail */}
      {!railCollapsed && (
        <aside className="hidden lg:flex w-[360px] shrink-0 flex-col border-r border-zinc-200/80 bg-white">
          {Sidebar}
        </aside>
      )}

      {/* Collapsed rail toggle */}
      {railCollapsed && (
        <div className="hidden lg:flex w-14 shrink-0 flex-col items-center border-r border-zinc-200/80 bg-white py-4">
          <button
            onClick={() => setRailCollapsed(false)}
            className="icon-btn"
            aria-label="Expand library"
            title="Expand library"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          <span className="mt-4 text-xl">🐼</span>
        </div>
      )}

      {/* Main workspace */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-zinc-200/80 bg-white/90 px-4 backdrop-blur lg:hidden">
          <button onClick={() => setMobileNavOpen(true)} className="icon-btn" aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </button>
          <Link href="/" className="flex items-center gap-2">
            <span className="text-lg">🐼</span>
            <span className="text-sm font-extrabold tracking-tight text-zinc-900">RFPANDA</span>
          </Link>
          <div className="w-8" />
        </header>

        <main className="min-h-0 flex-1 p-3 sm:p-5">
          <ChatInterface documents={documents} selectedDocIds={selectedDocIds} />
        </main>
      </div>

      {/* Mobile drawer */}
      {mobileNavOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-zinc-900/30 backdrop-blur-sm animate-fade-in lg:hidden"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 w-[88%] max-w-sm bg-white shadow-lift animate-drawer-left lg:hidden">
            {Sidebar}
          </aside>
        </>
      )}
    </div>
  );
}

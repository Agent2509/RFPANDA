// ============================================================================
// ApexTender v2.0 — Main Dashboard & RAG Workspace
// Combines Document Library, Direct Storage Upload, and Direct SSE Chat.
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
import {
  ShieldCheck,
  LogOut,
  LogIn,
  User,
  Layers,
  Sparkles,
  ExternalLink,
  Info,
} from 'lucide-react';
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

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.08),rgba(255,255,255,0))]">
      {/* Top Enterprise Navigation Bar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-slate-950 font-black">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-black tracking-tight text-white font-mono">
                RFPANDA <span className="text-emerald-400 font-sans font-bold text-xs">v2.0</span>
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800/80 text-emerald-300">
                Production RAG
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Free-Tier-Proof Enterprise Proposal Engine (Voyage 1024d + Groq Llama 3)
            </p>
          </div>
        </div>

        {/* Center / Right Telemetry & Auth */}
        <div className="flex items-center gap-4">
          {/* Backend RAM Diagnostic Badge */}
          <MemoryIndicator />

          {/* User Auth Section */}
          {!authLoading && user ? (
            <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
              <div className="hidden md:flex flex-col text-right">
                <span className="text-xs font-semibold text-slate-200 truncate max-w-[150px]">
                  {user.email}
                </span>
                <span className="text-[10px] text-emerald-400 font-mono">Tenant Authenticated</span>
              </div>

              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold text-xs">
                {user.email ? user.email.charAt(0).toUpperCase() : <User className="w-4 h-4" />}
              </div>

              <button
                onClick={signOut}
                title="Sign out"
                className="p-1.5 rounded-lg border border-slate-700 bg-slate-800/80 text-slate-400 hover:text-rose-400 hover:border-rose-800 hover:bg-rose-950/40 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : !authLoading ? (
            <Link href="/login">
              <Button size="sm" variant="primary" className="text-xs flex items-center gap-1.5">
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      {/* Main Responsive Grid Layout */}
      <main className="flex-1 p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-[1800px] w-full mx-auto overflow-hidden">
        {/* Left Column: Direct Upload Dropzone & Document Library (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-5 h-[calc(100vh-6.5rem)] overflow-hidden">
          {/* Direct Storage Upload Dropzone */}
          <div className="flex-shrink-0">
            <UploadDropzone onUploadSuccess={refreshDocuments} />
          </div>

          {/* Document Management Library */}
          <div className="flex-1 min-h-0">
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
        </div>

        {/* Right Column: Direct-to-FastAPI SSE Streaming Chat Workspace (7 cols) */}
        <div className="lg:col-span-7 h-[calc(100vh-6.5rem)]">
          <ChatInterface documents={documents} selectedDocIds={selectedDocIds} />
        </div>
      </main>
    </div>
  );
}

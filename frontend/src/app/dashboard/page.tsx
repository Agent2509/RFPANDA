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
  LogOut,
  LogIn,
  User,
  Menu,
  X,
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
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAF8] text-stone-900 font-sans">
      {/* Top Nav Bar */}
      <header className="h-14 border-b border-stone-200 bg-white/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🐼</span>
            <h1 className="text-lg font-bold tracking-tight text-stone-900">
              RFPANDA <span className="text-emerald-600 font-normal text-xs ml-1">v2.0</span>
            </h1>
          </div>
        </div>

        {/* Center / Right Telemetry & Auth */}
        <div className="flex items-center gap-4">
          {/* Backend RAM Diagnostic Badge */}
          <MemoryIndicator />

          {/* User Auth Section */}
          {!authLoading && user ? (
            <div className="flex items-center gap-3 pl-3 border-l border-stone-200">
              <div className="hidden md:flex flex-col text-right">
                <span className="text-xs font-semibold text-stone-700 truncate max-w-[150px]">
                  {user.email}
                </span>
                <span className="text-[10px] text-emerald-600 font-mono">Online</span>
              </div>

              <div className="w-8 h-8 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-600 font-bold text-xs">
                {user.email ? user.email.charAt(0).toUpperCase() : <User className="w-4 h-4" />}
              </div>

              <button
                onClick={signOut}
                title="Sign out"
                className="p-1.5 rounded-full border border-stone-200 bg-stone-50 text-stone-500 hover:text-rose-500 hover:border-rose-200 hover:bg-rose-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : !authLoading ? (
            <Link href="/login">
              <Button size="sm" variant="primary" className="text-xs flex items-center gap-1.5 rounded-full">
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Button>
            </Link>
          ) : null}

          {/* Sidebar Toggle */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-full hover:bg-stone-100 text-stone-600 transition-colors ml-2"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Area */}
      <main className="flex-1 w-full max-w-4xl mx-auto p-4 lg:p-6 flex flex-col h-[calc(100vh-3.5rem)]">
        <ChatInterface documents={documents} selectedDocIds={selectedDocIds} />
      </main>

      {/* Slide-out Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-stone-900/20 backdrop-blur-sm z-40 transition-opacity sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Slide-out Sidebar Panel */}
      <div 
        className={`fixed top-0 left-0 w-80 h-full bg-white z-50 shadow-2xl rounded-r-2xl overflow-hidden transition-transform duration-300 ease-in-out flex flex-col ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4 border-b border-stone-100 flex items-center justify-between bg-stone-50/50">
          <h2 className="font-semibold text-stone-800">Documents</h2>
          <button 
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 rounded-full hover:bg-stone-200 text-stone-500 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
          <div className="flex-shrink-0">
            <UploadDropzone onUploadSuccess={refreshDocuments} />
          </div>

          <div className="flex-1">
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
      </div>
    </div>
  );
}

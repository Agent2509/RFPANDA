// ============================================================================
// RFPANDA — Upload Dropzone
// Uploads directly to Supabase Storage (bypasses serverless body limits).
// ============================================================================

'use client';

import React, { useState, useRef } from 'react';
import { getSupabaseBrowserClient } from '@/lib/supabase-client';
import { Button, ProgressBar } from '@/components/ui';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';

interface UploadDropzoneProps {
  onUploadSuccess?: () => void;
}

export function UploadDropzone({ onUploadSuccess }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const supabase = getSupabaseBrowserClient();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file: File) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    const MAX_SIZE = 50 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setErrorMessage('File exceeds the 50MB limit.');
      return;
    }

    const validTypes = [
      'application/pdf',
      'text/plain',
      'text/markdown',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
    ];

    const isPdfOrText =
      validTypes.includes(file.type) ||
      file.name.endsWith('.pdf') ||
      file.name.endsWith('.txt') ||
      file.name.endsWith('.md') ||
      file.name.endsWith('.docx');

    if (!isPdfOrText) {
      setErrorMessage('Supported formats: PDF, DOCX, TXT, MD.');
      return;
    }

    setSelectedFile(file);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const executeUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setProgress(10);
    setUploadStatus('Verifying session...');
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        throw new Error('You must be signed in to upload documents.');
      }

      const documentId =
        typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
              const r = (Math.random() * 16) | 0;
              const v = c === 'x' ? r : (r & 0x3) | 0x8;
              return v.toString(16);
            });

      const sanitizedFileName = selectedFile.name.replace(/[^a-zA-Z0-9._-]/g, '_');
      const storagePath = `${user.id}/${documentId}/${sanitizedFileName}`;

      setUploadStatus('Registering document...');
      setProgress(25);

      const { error: dbError } = await supabase.from('documents').insert({
        id: documentId,
        user_id: user.id,
        name: selectedFile.name,
        storage_path: storagePath,
        file_size: selectedFile.size,
        mime_type: selectedFile.type || 'application/pdf',
        status: 'uploaded',
        keep_forever: false,
        last_queried_at: new Date().toISOString(),
        metadata: {
          original_name: selectedFile.name,
          client_uploaded_at: new Date().toISOString(),
        },
      });

      if (dbError) {
        throw new Error(`Failed to create database record: ${dbError.message}`);
      }

      setUploadStatus('Uploading to storage...');
      setProgress(50);

      let uploadResult = await supabase.storage
        .from('rfp-documents')
        .upload(storagePath, selectedFile, { cacheControl: '3600', upsert: true });

      if (uploadResult.error) {
        uploadResult = await supabase.storage
          .from('documents')
          .upload(storagePath, selectedFile, { cacheControl: '3600', upsert: true });

        if (uploadResult.error) {
          await supabase.from('documents').delete().eq('id', documentId);
          throw new Error(`Storage upload failed: ${uploadResult.error.message}`);
        }
      }

      setProgress(80);
      setUploadStatus('Starting ingestion...');

      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://localhost:54321';
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token || '';

      try {
        const edgeFunctionUrl = `${supabaseUrl.replace(/\/$/, '')}/functions/v1/process-document`;
        const res = await fetch(edgeFunctionUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ document_id: documentId, storage_path: storagePath }),
        });

        if (res.ok) {
          const resData = await res.json().catch(() => ({}));
          if (resData.status === 'awaiting_fallback_parse') {
            setSuccessMessage('Uploaded. Parser hit a rate limit — use Run fallback on the document.');
          } else {
            setSuccessMessage(`Uploaded ${formatFileSize(selectedFile.size)}. Processing now.`);
          }
        } else {
          setSuccessMessage(`Uploaded ${formatFileSize(selectedFile.size)}. Ingestion queued.`);
        }
      } catch {
        setSuccessMessage(`Uploaded ${formatFileSize(selectedFile.size)} to storage.`);
      }

      setProgress(100);
      setSelectedFile(null);
      onUploadSuccess?.();
    } catch (err: any) {
      setErrorMessage(err.message || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        setProgress(0);
        setUploadStatus(null);
      }, 2500);
    }
  };

  return (
    <div className="panel-muted p-3">
      <div className="mb-2.5 flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-white">
          <UploadCloud className="h-3.5 w-3.5" />
        </span>
        <div>
          <h3 className="text-xs font-bold text-zinc-800">Add a document</h3>
          <p className="text-[10px] text-zinc-400">PDF, DOCX, TXT, MD · up to 50MB</p>
        </div>
      </div>

      {/* Dropzone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-4 text-center transition-all ${
          isDragging
            ? 'border-brand-500 bg-brand-50'
            : selectedFile
            ? 'border-zinc-300 bg-white'
            : 'border-zinc-300 bg-white/60 hover:border-brand-400 hover:bg-brand-50/40'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          accept=".pdf,.txt,.md,.docx,application/pdf,text/plain"
          className="hidden"
        />

        {!selectedFile ? (
          <div className="flex flex-col items-center">
            <UploadCloud className="mb-2 h-5 w-5 text-zinc-400" />
            <p className="text-xs font-medium text-zinc-600">
              Drag &amp; drop, or <span className="font-semibold text-brand-600 underline underline-offset-2">browse</span>
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2 text-left">
            <div className="flex min-w-0 items-center gap-2.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-600">
                <FileText className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-zinc-800">{selectedFile.name}</p>
                <p className="text-[10px] text-zinc-400">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
              className="icon-btn h-6 w-6"
              aria-label="Remove file"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>

      {/* Progress */}
      {isUploading && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-[11px] text-zinc-500">
            <span className="flex items-center gap-1.5 font-medium">
              <Loader2 className="h-3 w-3 animate-spin text-brand-600" />
              {uploadStatus || 'Uploading...'}
            </span>
            <span className="font-mono font-semibold text-brand-600">{progress}%</span>
          </div>
          <ProgressBar value={progress} className="mt-1.5 h-1" />
        </div>
      )}

      {/* Messages */}
      {errorMessage && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-200/60 bg-rose-50 p-2.5 text-[11px] text-rose-700">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-emerald-200/60 bg-emerald-50 p-2.5 text-[11px] text-emerald-700">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Actions */}
      {selectedFile && !isUploading && (
        <div className="mt-3 flex justify-end gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={() => setSelectedFile(null)}>
            Cancel
          </Button>
          <Button type="button" size="sm" onClick={executeUpload} className="gap-1.5">
            <UploadCloud className="h-3.5 w-3.5" />
            Upload
          </Button>
        </div>
      )}
    </div>
  );
}

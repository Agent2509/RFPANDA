// ============================================================================
// ApexTender v2.0 — Direct Supabase Storage Upload Dropzone
// Directly uploads files (>10MB to 50MB) to Supabase Storage bucket `rfp-documents`
// at `{user_id}/{document_id}/{filename}`, completely bypassing Vercel's 4.5MB limit.
// ============================================================================

'use client';

import React, { useState, useRef } from 'react';
import { getSupabaseBrowserClient } from '@/lib/supabase-client';
import { Button } from '@/components/ui';
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

  const handleDragLeave = () => {
    setIsDragging(false);
  };

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

    // Max 50MB
    const MAX_SIZE = 50 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setErrorMessage('File size exceeds the 50MB free-tier limit.');
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
      setErrorMessage('Supported file formats: PDF, DOCX, TXT, MD.');
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

      const documentId = typeof crypto.randomUUID === 'function'
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

      // Step 1: Insert document metadata in database with status 'uploaded'
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

      setUploadStatus('Direct upload to Supabase Storage (Bypassing Vercel 4.5MB limit)...');
      setProgress(50);

      // Step 2: Direct browser upload to Supabase Storage bucket 'rfp-documents'
      let uploadResult = await supabase.storage
        .from('rfp-documents')
        .upload(storagePath, selectedFile, {
          cacheControl: '3600',
          upsert: true,
        });

      if (uploadResult.error) {
        // Fallback to 'documents' bucket if 'rfp-documents' is not found
        uploadResult = await supabase.storage
          .from('documents')
          .upload(storagePath, selectedFile, {
            cacheControl: '3600',
            upsert: true,
          });

        if (uploadResult.error) {
          await supabase.from('documents').delete().eq('id', documentId);
          throw new Error(`Storage upload failed: ${uploadResult.error.message}`);
        }
      }

      setProgress(80);
      setUploadStatus('Triggering background ingestion pipeline...');

      // Step 3: Trigger Edge Function `process-document`
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
          body: JSON.stringify({
            document_id: documentId,
            storage_path: storagePath,
          }),
        });

        if (res.ok) {
          const resData = await res.json().catch(() => ({}));
          if (resData.status === 'awaiting_fallback_parse') {
            setSuccessMessage('Uploaded! Primary parser reached rate limits. Ready for client-side PDF.js parsing.');
          } else {
            setSuccessMessage(`Document uploaded & scheduled for processing! (${formatFileSize(selectedFile.size)})`);
          }
        } else {
          setSuccessMessage(`Document uploaded (${formatFileSize(selectedFile.size)}). Ingestion queued.`);
        }
      } catch {
        // Even if Edge Function invoke fails, document is uploaded safely in storage
        setSuccessMessage(`Document uploaded to storage (${formatFileSize(selectedFile.size)}).`);
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
    <div className="w-full bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-emerald-400" />
            Upload RFP Document
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Direct-to-storage upload bypassing Vercel's 4.5MB limit (Up to 50MB supported)
          </p>
        </div>
      </div>

      {/* Dropzone container */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-emerald-500 bg-emerald-950/20'
            : selectedFile
            ? 'border-slate-700 bg-slate-850/50'
            : 'border-slate-800 hover:border-slate-700 hover:bg-slate-850/30'
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
            <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400 mb-3 group-hover:text-emerald-400">
              <UploadCloud className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-slate-200">
              Drag & drop your RFP here, or <span className="text-emerald-400 font-semibold underline">browse</span>
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports large PDFs, DOCX, TXT, and Markdown files
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-between bg-slate-800/80 p-3 rounded-lg border border-slate-700">
            <div className="flex items-center gap-3 overflow-hidden text-left">
              <div className="w-10 h-10 rounded-lg bg-emerald-950 border border-emerald-800/60 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="truncate">
                <p className="text-sm font-semibold text-slate-100 truncate">{selectedFile.name}</p>
                <p className="text-xs text-slate-400">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
              className="p-1 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Progress Bar & Status */}
      {isUploading && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <span className="flex items-center gap-1.5 font-medium">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
              {uploadStatus || 'Uploading...'}
            </span>
            <span className="font-semibold text-emerald-400">{progress}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-emerald-400 h-1.5 transition-all duration-300 ease-out rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error / Success Messages */}
      {errorMessage && (
        <div className="mt-3 p-3 rounded-lg bg-rose-950/50 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div className="mt-3 p-3 rounded-lg bg-emerald-950/50 border border-emerald-800/50 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Upload Action Button */}
      {selectedFile && !isUploading && (
        <div className="mt-4 flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setSelectedFile(null)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={executeUpload}
            className="flex items-center gap-1.5"
          >
            <UploadCloud className="w-4 h-4" />
            Upload {formatFileSize(selectedFile.size)}
          </Button>
        </div>
      )}
    </div>
  );
}

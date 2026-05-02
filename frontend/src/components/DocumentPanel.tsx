'use client';

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, FileText, Trash2, Eye, Loader2, CloudDownload,
  FileIcon, CheckCircle, AlertCircle, XCircle
} from 'lucide-react';
import { api, DocumentInfo } from '@/lib/api';
import { useEffect } from 'react';

export function DocumentPanel() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [summary, setSummary] = useState<{ id: string; text: string } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await api.getDocuments();
      setDocuments(data.documents || []);
    } catch {}
  };

  const handleUpload = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(file);
      }
      await loadDocuments();
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDocument(id);
      setDocuments(prev => prev.filter(d => d.id !== id));
    } catch {}
  };

  const handleSummarize = async (id: string) => {
    try {
      setSummary({ id, text: 'Generating summary...' });
      const result = await api.summarizeDocument(id);
      setSummary({ id, text: result.summary });
    } catch {
      setSummary({ id, text: 'Failed to generate summary.' });
    }
  };

  const handleIngestMock = async (source: string) => {
    try {
      await api.ingestMockData(source);
      await loadDocuments();
    } catch {}
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'ready': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'processing': return <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-400" />;
      default: return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Document Management</h2>
          <p className="text-gray-400">Upload, manage, and query your knowledge base documents.</p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`glass-card p-8 mb-8 text-center cursor-pointer transition-all duration-300 ${
            dragOver ? 'border-primary-500/50 bg-primary-500/5 scale-[1.01]' : 'hover:border-white/[0.15]'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            multiple
            onChange={(e) => handleUpload(e.target.files)}
            className="hidden"
          />

          {isUploading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-10 h-10 text-primary-400 animate-spin" />
              <p className="text-gray-300">Processing documents...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center">
                <Upload className="w-8 h-8 text-primary-400" />
              </div>
              <div>
                <p className="text-white font-medium">Drop files here or click to upload</p>
                <p className="text-gray-500 text-sm mt-1">Supports PDF, DOCX, TXT, MD (Max 50MB)</p>
              </div>
            </div>
          )}
        </div>

        {/* Mock Data Ingestion */}
        <div className="flex gap-3 mb-8">
          <button
            onClick={() => handleIngestMock('slack')}
            className="glass-button-secondary flex items-center gap-2 text-sm"
          >
            <CloudDownload className="w-4 h-4" />
            Import Slack Data
          </button>
          <button
            onClick={() => handleIngestMock('notion')}
            className="glass-button-secondary flex items-center gap-2 text-sm"
          >
            <CloudDownload className="w-4 h-4" />
            Import Notion Data
          </button>
        </div>

        {/* Documents List */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white mb-4">
            Documents ({documents.length})
          </h3>

          <AnimatePresence>
            {documents.map((doc) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="glass-card p-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-white/[0.05] flex items-center justify-center">
                      <FileText className="w-5 h-5 text-primary-400" />
                    </div>
                    <div>
                      <h4 className="text-white font-medium text-sm">{doc.filename}</h4>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-gray-500 uppercase">{doc.file_type.replace('.', '')}</span>
                        <span className="text-xs text-gray-500">{formatSize(doc.file_size)}</span>
                        <span className="text-xs text-gray-500">{doc.chunk_count} chunks</span>
                        <div className="flex items-center gap-1">
                          {statusIcon(doc.status)}
                          <span className="text-xs text-gray-500 capitalize">{doc.status}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => window.open(`/api/v1/documents/${doc.id}/view`, '_blank')}
                      className="p-2 hover:bg-white/[0.05] rounded-lg transition-colors"
                      title="View Document"
                    >
                      <Eye className="w-4 h-4 text-gray-400 hover:text-primary-400" />
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                    </button>
                  </div>
                </div>

                {/* Summary */}
                {summary?.id === doc.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="mt-4 pt-4 border-t border-white/[0.06]"
                  >
                    <p className="text-sm text-gray-300">{summary.text}</p>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {documents.length === 0 && (
            <div className="glass-card p-12 text-center">
              <FileIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No documents uploaded yet</p>
              <p className="text-gray-600 text-sm mt-1">Upload files or import mock data to get started</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

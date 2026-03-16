import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Trash2, RefreshCw, Database } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { documentsApi } from '../api';
import type { DocumentInfo } from './types';
import { StatusBadge, EmptyState, Spinner } from '../components/ui';

const FILE_TYPE_ICONS: Record<string, string> = {
  '.pdf': '📄',
  '.txt': '📝',
  '.md':  '📋',
  '.html':'🌐',
  '.docx':'📘',
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await documentsApi.list();
      setDocuments(docs);
    } catch {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    // Poll for status updates
    const interval = setInterval(loadDocuments, 5000);
    return () => clearInterval(interval);
  }, [loadDocuments]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true);
    for (const file of acceptedFiles) {
      try {
        setUploadProgress(p => ({ ...p, [file.name]: 0 }));
        await documentsApi.upload(file);
        setUploadProgress(p => ({ ...p, [file.name]: 100 }));
        toast.success(`"${file.name}" uploaded — indexing in progress`);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed';
        toast.error(`Failed to upload "${file.name}": ${msg}`);
      }
    }
    setUploading(false);
    setUploadProgress({});
    await loadDocuments();
  }, [loadDocuments]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/html': ['.html'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 50 * 1024 * 1024,
  });

  const deleteDocument = async (docId: string, filename: string) => {
    if (!confirm(`Delete "${filename}" from the knowledge base?`)) return;
    try {
      await documentsApi.delete(docId);
      toast.success('Document removed');
      await loadDocuments();
    } catch {
      toast.error('Failed to delete document');
    }
  };

  const indexedCount = documents.filter(d => d.status === 'indexed').length;
  const totalChunks = documents.reduce((a, d) => a + (d.chunk_count || 0), 0);

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-5 flex items-center justify-between"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div>
          <h1 className="font-display text-xl" style={{ color: 'var(--text-primary)' }}>
            Knowledge Sources
          </h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            Upload documents to build the research knowledge base
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Stats */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ background: 'var(--bg-elevated)' }}>
            <Database size={13} style={{ color: '#60a5fa' }} />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {indexedCount} docs · {totalChunks.toLocaleString()} chunks
            </span>
          </div>
          <button onClick={loadDocuments} className="btn-ghost">
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-6 space-y-6">
        {/* Dropzone */}
        <div
          {...getRootProps()}
          className="border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200"
          style={{
            borderColor: isDragActive ? '#3b82f6' : 'var(--border-active)',
            background: isDragActive ? 'rgba(59,130,246,0.05)' : 'var(--bg-card)',
          }}
        >
          <input {...getInputProps()} />
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: isDragActive ? 'rgba(59,130,246,0.2)' : 'var(--bg-elevated)' }}>
            {uploading ? (
              <Spinner size={24} />
            ) : (
              <Upload size={24} style={{ color: isDragActive ? '#60a5fa' : 'var(--text-muted)' }} />
            )}
          </div>
          <p className="font-medium text-sm mb-1" style={{ color: 'var(--text-primary)' }}>
            {isDragActive ? 'Drop files here...' : 'Drag & drop documents'}
          </p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            PDF, TXT, Markdown, HTML, DOCX · Max 50 MB each
          </p>
          {Object.keys(uploadProgress).length > 0 && (
            <div className="mt-4 space-y-1">
              {Object.entries(uploadProgress).map(([name]) => (
                <p key={name} className="text-xs" style={{ color: '#60a5fa' }}>
                  ↑ Uploading {name}...
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Document list */}
        <div>
          <h2 className="text-xs font-medium uppercase tracking-wider mb-3"
            style={{ color: 'var(--text-muted)' }}>
            Indexed Documents ({documents.length})
          </h2>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner size={24} />
            </div>
          ) : documents.length === 0 ? (
            <EmptyState
              icon={<FileText size={22} />}
              title="No documents yet"
              description="Upload PDFs, text files, or HTML pages to build your knowledge base."
            />
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <DocumentRow
                  key={doc.doc_id}
                  doc={doc}
                  onDelete={() => deleteDocument(doc.doc_id, doc.filename)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: DocumentInfo;
  onDelete: () => void;
}) {
  const icon = FILE_TYPE_ICONS[doc.file_type] || '📁';
  const isProcessing = doc.status === 'processing' || doc.status === 'pending';

  return (
    <div className="card flex items-center gap-4 px-4 py-3 hover:border-opacity-50 transition-all duration-150"
      style={{ borderColor: doc.status === 'failed' ? 'rgba(244,63,94,0.2)' : 'var(--border)' }}>
      {/* Icon */}
      <div className="text-2xl">{icon}</div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
            {doc.filename}
          </p>
          {isProcessing && <Spinner size={12} />}
        </div>
        <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span>{formatFileSize(doc.file_size)}</span>
          {doc.chunk_count > 0 && (
            <>
              <span>·</span>
              <span>{doc.chunk_count} chunks</span>
            </>
          )}
          <span>·</span>
          <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
          {doc.error && (
            <>
              <span>·</span>
              <span style={{ color: '#fb7185' }}>{doc.error}</span>
            </>
          )}
        </div>
      </div>

      {/* Status */}
      <StatusBadge status={doc.status} />

      {/* Delete */}
      <button
        onClick={onDelete}
        className="btn-ghost p-1.5 ml-1"
        title="Remove document"
      >
        <Trash2 size={13} style={{ color: 'var(--text-muted)' }} />
      </button>
    </div>
  );
}

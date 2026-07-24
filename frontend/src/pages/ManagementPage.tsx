import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Settings, ShieldCheck, UploadCloud, Trash2, Loader2, FileText, CheckCircle2, Clock, AlertTriangle, RefreshCw } from 'lucide-react';
import { fileService } from '../services/fileService';
import type { FileItemResponse } from '../types/files';

/** Format bytes to human-readable KB/MB/GB */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/** Format unix timestamp to readable date string */
function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Render sync status badge */
function SyncStatusBadge({ status }: { status: number }) {
  switch (status) {
    case 1:
      return (
        <span className="inline-flex items-center space-x-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" />
          <span>Synced</span>
        </span>
      );
    case 2:
      return (
        <span className="inline-flex items-center space-x-1 text-[10px] font-semibold text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">
          <AlertTriangle className="w-3 h-3" />
          <span>Failed</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center space-x-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
          <Clock className="w-3 h-3" />
          <span>Pending</span>
        </span>
      );
  }
}

export const ManagementPage: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [files, setFiles] = useState<FileItemResponse[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [lastCursor, setLastCursor] = useState<string>('');
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletedIds, setDeletedIds] = useState<Set<number>>(new Set());

  const fetchFiles = useCallback(async (cursor?: string) => {
    setIsLoadingFiles(true);
    try {
      const res = await fileService.listFiles(cursor);
      if (res.code === 0) {
        if (cursor) {
          setFiles((prev) => [...prev, ...res.data.items]);
        } else {
          setFiles(res.data.items);
        }
        setLastCursor(res.data.last_cursor || '');
      }
    } catch {
      // Error handled silently in UI
    } finally {
      setIsLoadingFiles(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadSuccess(null);
    setUploadError(null);

    try {
      const res = await fileService.uploadFile(file);
      if (res.code === 0) {
        setUploadSuccess(`File "${res.data.file_name}" uploaded successfully.`);
        // Refresh the file list
        await fetchFiles();
      } else {
        setUploadError(res.message || 'Upload failed.');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed due to unknown error.';
      setUploadError(message);
    } finally {
      setIsUploading(false);
      // Reset file input so the same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = (fileId: number) => {
    // UI-only deletion: hide the row from the list without backend call
    setDeletedIds((prev) => new Set(prev).add(fileId));
  };

  const handleLoadMore = () => {
    if (lastCursor) {
      fetchFiles(lastCursor);
    }
  };

  const visibleFiles = files.filter((f) => !deletedIds.has(f.file_id));

  // Auto-dismiss success/error messages
  useEffect(() => {
    if (uploadSuccess) {
      const timer = setTimeout(() => setUploadSuccess(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [uploadSuccess]);

  useEffect(() => {
    if (uploadError) {
      const timer = setTimeout(() => setUploadError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [uploadError]);

  return (
    <div className="flex-1 h-[calc(100vh-4rem)] flex flex-col glass-panel overflow-hidden">
      {/* Management Header */}
      <div className="p-4 border-b border-border/60 flex items-center justify-between bg-muted/20">
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-foreground text-sm">
            Tenant Administration Console
          </h2>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
            <ShieldCheck className="w-3.5 h-3.5 mr-1" />
            <span>Admin Access Verified</span>
          </div>
          <button
            onClick={() => fetchFiles()}
            disabled={isLoadingFiles}
            className="flex items-center space-x-1.5 py-2 px-3 rounded-xl border border-border text-foreground hover:bg-muted/40 font-medium text-xs transition-all disabled:opacity-50"
            title="Refresh file list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingFiles ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            id="upload-file-button"
            onClick={handleUploadClick}
            disabled={isUploading}
            className="flex items-center space-x-1.5 py-2 px-4 rounded-xl bg-primary text-primary-foreground font-medium text-xs hover:opacity-90 transition-all shadow-md shadow-blue-500/20 disabled:opacity-50"
          >
            {isUploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <UploadCloud className="w-3.5 h-3.5" />
            )}
            <span>{isUploading ? 'Uploading...' : 'Upload File'}</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.pdf"
            onChange={handleFileChange}
            className="hidden"
            data-testid="file-input"
          />
        </div>
      </div>

      {/* Toast messages */}
      {uploadSuccess && (
        <div className="mx-4 mt-3 p-3 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium flex items-center space-x-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}
      {uploadError && (
        <div className="mx-4 mt-3 p-3 rounded-xl bg-red-600/10 border border-red-500/20 text-red-400 text-xs font-medium flex items-center space-x-2 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* File List */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoadingFiles && files.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full space-y-3 text-muted-foreground">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <span className="text-sm">Loading files...</span>
          </div>
        ) : visibleFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full space-y-3 text-muted-foreground">
            <FileText className="w-12 h-12 text-slate-600" />
            <p className="text-sm font-medium">No files uploaded yet</p>
            <p className="text-xs">Click the "Upload File" button to upload your first document.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Table Header */}
            <div className="grid grid-cols-[1fr_80px_60px_140px_160px_90px_50px] gap-3 px-4 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border/40">
              <span>File Name</span>
              <span>Size</span>
              <span>Type</span>
              <span>Uploaded</span>
              <span>Owner</span>
              <span>Sync</span>
              <span></span>
            </div>

            {/* File Rows */}
            {visibleFiles.map((file) => (
              <div
                key={file.file_id}
                className="grid grid-cols-[1fr_80px_60px_140px_160px_90px_50px] gap-3 items-center px-4 py-3 rounded-xl bg-slate-900/40 border border-border/40 hover:border-indigo-500/30 transition-all group"
              >
                <div className="flex items-center space-x-2 min-w-0">
                  <FileText className="w-4 h-4 text-blue-400 shrink-0" />
                  <span className="text-sm text-foreground font-medium truncate" title={file.file_name}>
                    {file.file_name}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  {formatFileSize(file.file_size)}
                </span>
                <span className="text-xs text-muted-foreground font-mono uppercase">
                  {file.file_type}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatTimestamp(file.create_ts)}
                </span>
                <span className="text-xs text-muted-foreground truncate" title={file.owner_email}>
                  {file.owner_email}
                </span>
                <SyncStatusBadge status={file.vector_db_sync_status} />
                <button
                  onClick={() => handleDelete(file.file_id)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                  title="Delete file (UI only)"
                  data-testid={`delete-file-${file.file_id}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {/* Load More */}
            {lastCursor && (
              <div className="flex justify-center pt-2">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoadingFiles}
                  className="flex items-center space-x-1.5 py-2 px-4 rounded-xl border border-border text-foreground hover:bg-muted/40 font-medium text-xs transition-all disabled:opacity-50"
                >
                  {isLoadingFiles ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : null}
                  <span>Load More</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ManagementPage;

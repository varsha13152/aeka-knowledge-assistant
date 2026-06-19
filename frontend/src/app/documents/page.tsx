'use client';

/**
 * Document management page — upload, view, and delete documents.
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Document {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  created_at: string;
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.listDocuments(),
  });
  const documents = data?.documents ?? [];

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.uploadDocument(file);
      setUploadProgress('Processing document...');
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
      setUploadProgress('');
    } catch (err: any) {
      setUploadProgress(`Error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document and all its chunks?')) return;

    try {
      await api.deleteDocument(id);
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Documents</h1>
          <p className="text-sm text-gray-500">Upload and manage your knowledge base</p>
        </div>
        <label className="cursor-pointer rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Upload Document
          <input
            type="file"
            className="hidden"
            accept=".pdf,.docx,.md,.txt"
            onChange={handleUpload}
            disabled={isUploading}
          />
        </label>
      </div>

      {uploadProgress && (
        <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-700">
          {uploadProgress}
        </div>
      )}

      <div className="rounded-xl border bg-white shadow-sm">
        {documents.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-400">No documents uploaded yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Upload PDFs, DOCX, or Markdown files to build your knowledge base
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Filename</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Size</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Chunks</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Uploaded</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{doc.filename}</td>
                  <td className="px-4 py-3 text-gray-500">{formatSize(doc.file_size)}</td>
                  <td className="px-4 py-3 text-gray-500">{doc.chunk_count}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        doc.status === 'ready'
                          ? 'bg-green-100 text-green-700'
                          : doc.status === 'processing'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-500 hover:text-red-700 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

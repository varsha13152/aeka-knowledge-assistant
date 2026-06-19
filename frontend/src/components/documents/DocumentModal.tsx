'use client';

/**
 * Full-screen document viewer modal.
 *
 * Opens over the chat when a citation is clicked. Supports:
 * - PDF rendering with page navigation (via react-pdf)
 * - Text/Markdown rendering with cited text highlighted
 * - Keyboard shortcut (Escape) to dismiss
 */

import { useCallback, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { api } from '@/lib/api';
import ReactMarkdown from 'react-markdown';

// Lazy-load PdfViewer (~800KB) — only loaded when a PDF citation is clicked
const PdfViewer = dynamic(() => import('./PdfViewer').then((m) => ({ default: m.PdfViewer })), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-gray-500">Loading PDF viewer...</div>
  ),
});

interface DocumentModalProps {
  documentId: string;
  filename: string;
  contentType: string;
  initialPage?: number;
  highlightText?: string;
  onClose: () => void;
}

export function DocumentModal({
  documentId,
  filename,
  contentType,
  initialPage = 1,
  highlightText,
  onClose,
}: DocumentModalProps) {
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isPdf = contentType === 'application/pdf';

  // Fetch the document URL from the backend
  useEffect(() => {
    let cancelled = false;

    async function fetchDocument() {
      try {
        setLoading(true);
        const { url } = await api.getDocumentUrl(documentId);

        if (cancelled) return;

        if (isPdf) {
          setDocumentUrl(url);
        } else {
          // For text/markdown, fetch the content directly
          const response = await fetch(url);
          const text = await response.text();
          if (!cancelled) setTextContent(text);
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to load document');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchDocument();
    return () => { cancelled = true; };
  }, [documentId, isPdf]);

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Highlight matching text in content
  const renderTextContent = useCallback(() => {
    if (!textContent) return null;

    if (highlightText) {
      const idx = textContent.toLowerCase().indexOf(highlightText.toLowerCase().slice(0, 60));
      if (idx !== -1) {
        const before = textContent.slice(0, idx);
        const match = textContent.slice(idx, idx + highlightText.length);
        const after = textContent.slice(idx + highlightText.length);
        return (
          <div className="prose prose-sm max-w-none p-6">
            <ReactMarkdown>{before}</ReactMarkdown>
            <mark className="bg-yellow-200 rounded px-0.5">{match}</mark>
            <ReactMarkdown>{after}</ReactMarkdown>
          </div>
        );
      }
    }

    return (
      <div className="prose prose-sm max-w-none p-6">
        <ReactMarkdown>{textContent}</ReactMarkdown>
      </div>
    );
  }, [textContent, highlightText]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={`Document viewer: ${filename}`}>
      <div className="relative flex h-[90vh] w-[90vw] max-w-5xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-lg">📄</span>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">{filename}</h3>
              {isPdf && initialPage > 1 && (
                <span className="text-xs text-gray-500">
                  Cited from page {initialPage}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            title="Close (Escape)"
          >
            ✕
          </button>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-hidden">
          {loading && (
            <div className="flex h-full items-center justify-center text-gray-500">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                <span>Loading document...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="flex h-full items-center justify-center text-red-500">
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && isPdf && documentUrl && (
            <PdfViewer url={documentUrl} initialPage={initialPage} />
          )}

          {!loading && !error && !isPdf && (
            <div className="h-full overflow-y-auto">
              {renderTextContent()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

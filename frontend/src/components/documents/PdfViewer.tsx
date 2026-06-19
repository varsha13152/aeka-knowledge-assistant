'use client';

/**
 * PDF viewer using react-pdf with page navigation.
 *
 * Renders a single page at a time with controls to navigate between pages.
 * Scrolls to the specified initialPage on mount and when the prop changes.
 */

import { useCallback, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker — self-hosted via node_modules copy in next.config.js
// Falls back to inline worker if the file is not found
pdfjs.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.mjs`;

interface PdfViewerProps {
  url: string;
  initialPage?: number;
}

export function PdfViewer({ url, initialPage = 1 }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [pageInput, setPageInput] = useState<string>(String(initialPage));

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    // Clamp initial page to valid range
    const page = Math.min(Math.max(1, initialPage), numPages);
    setCurrentPage(page);
    setPageInput(String(page));
  }, [initialPage]);

  const goToPage = (page: number) => {
    const clamped = Math.min(Math.max(1, page), numPages);
    setCurrentPage(clamped);
    setPageInput(String(clamped));
  };

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const page = parseInt(pageInput, 10);
    if (!isNaN(page)) goToPage(page);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Page navigation controls */}
      <div className="flex items-center justify-between border-b bg-gray-50 px-3 py-2">
        <button
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage <= 1}
          className="rounded px-2 py-1 text-sm hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ← Prev
        </button>

        <form onSubmit={handlePageInputSubmit} className="flex items-center gap-1 text-sm">
          <span>Page</span>
          <input
            type="text"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            className="w-12 rounded border border-gray-300 px-1 py-0.5 text-center text-sm"
          />
          <span>of {numPages}</span>
        </form>

        <button
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage >= numPages}
          className="rounded px-2 py-1 text-sm hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next →
        </button>
      </div>

      {/* PDF page render */}
      <div className="flex-1 overflow-auto flex justify-center bg-gray-100 p-4">
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div className="flex items-center justify-center py-20 text-gray-500">
              Loading PDF...
            </div>
          }
          error={
            <div className="flex items-center justify-center py-20 text-red-500">
              Failed to load PDF
            </div>
          }
        >
          <Page
            pageNumber={currentPage}
            width={550}
            renderTextLayer={true}
            renderAnnotationLayer={true}
          />
        </Document>
      </div>
    </div>
  );
}

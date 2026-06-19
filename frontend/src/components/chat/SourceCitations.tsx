'use client';

/**
 * Source citations component — clickable cards showing retrieved sources.
 *
 * Clicking a citation opens the document viewer modal at the cited page.
 */

import { useState } from 'react';
import { useChatStore } from '@/stores/chatStore';
import type { Source } from '@/stores/chatStore';

interface SourceCitationsProps {
  sources: Source[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [expanded, setExpanded] = useState(false);
  const openDocumentViewer = useChatStore((s) => s.openDocumentViewer);

  if (!sources || sources.length === 0) return null;

  const handleSourceClick = (source: Source) => {
    openDocumentViewer({
      documentId: source.document_id,
      filename: source.filename || 'Document',
      contentType: source.content_type || 'application/pdf',
      page: source.page_start || 1,
      highlightText: source.content_preview,
    });
  };

  return (
    <div className="mt-2 border-t pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand-600"
        aria-expanded={expanded}
        aria-label={`${sources.length} source${sources.length > 1 ? 's' : ''} cited. Click to ${expanded ? 'collapse' : 'expand'}.`}
      >
        <span aria-hidden="true">{expanded ? '▼' : '▶'}</span>
        <span>{sources.length} source{sources.length > 1 ? 's' : ''} cited</span>
      </button>

      {expanded && (
        <div className="mt-2 space-y-2">
          {sources.map((source, index) => (
            <button
              key={source.chunk_id}
              onClick={() => handleSourceClick(source)}
              className="w-full rounded-lg border border-gray-100 bg-gray-50 p-2.5 text-xs text-left hover:border-brand-300 hover:bg-brand-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-brand-700">
                  [Source {index + 1}]
                  {source.filename && (
                    <span className="ml-1.5 font-normal text-gray-600">
                      {source.filename}
                    </span>
                  )}
                </span>
                <div className="flex items-center gap-2">
                  {source.page_start && (
                    <span className="text-gray-500">
                      p.{source.page_start}
                      {source.page_end && source.page_end !== source.page_start && `–${source.page_end}`}
                    </span>
                  )}
                  <span className="text-gray-400">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <p className="text-gray-600 line-clamp-2">
                {source.content_preview}
              </p>
              <span className="mt-1 inline-block text-brand-600 text-[10px] font-medium">
                Click to view →
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

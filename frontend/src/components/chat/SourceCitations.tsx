'use client';

/**
 * Source citations component — collapsible cards showing retrieved sources.
 */

import { useState } from 'react';
import type { Source } from '@/stores/chatStore';

interface SourceCitationsProps {
  sources: Source[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2 border-t pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand-600"
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span>{sources.length} source{sources.length > 1 ? 's' : ''} cited</span>
      </button>

      {expanded && (
        <div className="mt-2 space-y-2">
          {sources.map((source, index) => (
            <div
              key={source.chunk_id}
              className="rounded-lg border border-gray-100 bg-gray-50 p-2.5 text-xs"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-brand-700">
                  [Source {index + 1}]
                </span>
                <span className="text-gray-400">
                  relevance: {(source.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-gray-600 line-clamp-3">
                {source.content_preview}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

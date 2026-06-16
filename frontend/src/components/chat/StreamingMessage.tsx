'use client';

/**
 * Streaming message component — renders partial markdown content with a typing cursor.
 */

import { MarkdownMessage } from './MarkdownMessage';

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="max-w-[80%] rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm">
      <div className="prose-chat text-sm">
        <MarkdownMessage content={content} />
        <span className="streaming-cursor" />
      </div>
    </div>
  );
}

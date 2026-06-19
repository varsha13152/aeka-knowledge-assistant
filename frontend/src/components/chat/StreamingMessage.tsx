'use client';

/**
 * Streaming message component — renders partial content with a typing cursor.
 *
 * Performance: Uses plain text during streaming (not markdown) to avoid
 * re-parsing the entire content on every token. Markdown is rendered only
 * after streaming completes (in MessageBubble via MarkdownMessage).
 */

import { memo, useEffect, useRef, useState } from 'react';

interface StreamingMessageProps {
  content: string;
}

export const StreamingMessage = memo(function StreamingMessage({ content }: StreamingMessageProps) {
  // Throttle renders to max once per 50ms for smooth display without jank
  const [displayed, setDisplayed] = useState(content);
  const rafRef = useRef<number | null>(null);
  const latestContent = useRef(content);

  latestContent.current = content;

  useEffect(() => {
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(() => {
        setDisplayed(latestContent.current);
        rafRef.current = null;
      });
    }
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [content]);

  return (
    <div className="max-w-[80%] rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm">
      <div className="prose-chat text-sm whitespace-pre-wrap">
        {displayed}
        <span className="inline-block w-2 h-4 ml-0.5 bg-brand-500 animate-pulse rounded-sm" />
      </div>
    </div>
  );
});

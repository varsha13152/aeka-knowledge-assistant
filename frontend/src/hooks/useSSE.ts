/**
 * Custom hook for Server-Sent Events (SSE) streaming.
 *
 * Handles:
 * - EventSource connection lifecycle
 * - Typed event parsing (sources, token, done, error)
 * - Automatic reconnection
 * - Cleanup on unmount
 */

import { useCallback, useRef } from 'react';
import { useChatStore } from '@/stores/chatStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChatRequestOptions {
  message: string;
  sessionId?: string;
  useRag?: boolean;
  maxContextTokens?: number;
}

export function useSSE() {
  const abortControllerRef = useRef<AbortController | null>(null);
  const {
    addMessage,
    updateStreamingContent,
    finalizeStreaming,
    addAgentStep,
    clearAgentSteps,
    setLoading,
    setStreaming,
  } = useChatStore();

  const sendMessage = useCallback(async (options: ChatRequestOptions) => {
    const { message, sessionId, useRag = true, maxContextTokens = 4096 } = options;

    // Add user message immediately
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      createdAt: new Date().toISOString(),
    });

    setLoading(true);
    clearAgentSteps();

    // Abort any existing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_URL}/api/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          use_rag: useRag,
          stream: true,
          max_context_tokens: maxContextTokens,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      setStreaming(true);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim();
            continue;
          }

          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              handleSSEEvent(parsed);
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        addMessage({
          id: crypto.randomUUID(),
          role: 'system',
          content: `Error: ${error.message}`,
          createdAt: new Date().toISOString(),
        });
      }
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  }, [addMessage, updateStreamingContent, finalizeStreaming, addAgentStep, clearAgentSteps, setLoading, setStreaming]);

  const handleSSEEvent = useCallback((data: any) => {
    // Token event: append to streaming content
    if (data.content !== undefined && !data.is_final) {
      updateStreamingContent(data.content);
    }

    // Sources event: store for display
    if (Array.isArray(data) && data[0]?.chunk_id) {
      addAgentStep({ node: 'retrieval', action: 'sources_retrieved', sources: data });
    }

    // Done event: finalize the message
    if (data.input_tokens !== undefined || data.is_final) {
      finalizeStreaming(data);
    }

    // Error event
    if (data.error) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `Error: ${data.error}`,
        createdAt: new Date().toISOString(),
      });
    }
  }, [updateStreamingContent, addAgentStep, finalizeStreaming, addMessage]);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    setStreaming(false);
    setLoading(false);
  }, [setStreaming, setLoading]);

  return { sendMessage, abort };
}

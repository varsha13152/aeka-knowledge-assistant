/**
 * Custom hook for Server-Sent Events (SSE) streaming.
 *
 * Handles:
 * - EventSource connection lifecycle
 * - Typed event parsing (sources, token, done, error, agent_step)
 * - Cleanup on unmount
 */

import { useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useChatStore } from '@/stores/chatStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChatRequestOptions {
  message: string;
  sessionId?: string;
  useRag?: boolean;
  maxContextTokens?: number;
}

export function useSSE() {
  const { getToken } = useAuth();
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

  const handleSSEEvent = useCallback((eventType: string, data: any) => {
    switch (eventType) {
      case 'token':
        if (data.content !== undefined) {
          updateStreamingContent(data.content);
        }
        break;

      case 'sources':
        addAgentStep({ node: 'retrieval', action: 'sources_retrieved', sources: data });
        break;

      case 'agent_step':
        addAgentStep(data);
        break;

      case 'done':
        finalizeStreaming(data);
        break;

      case 'error':
        addMessage({
          id: crypto.randomUUID(),
          role: 'system',
          content: `Error: ${data.error || 'An unknown error occurred'}`,
          createdAt: new Date().toISOString(),
        });
        break;

      default:
        // Unknown event type — try heuristic fallback for backward compat
        if (data.content !== undefined && !data.is_final) {
          updateStreamingContent(data.content);
        } else if (data.is_final || data.input_tokens !== undefined) {
          finalizeStreaming(data);
        }
        break;
    }
  }, [updateStreamingContent, addAgentStep, finalizeStreaming, addMessage]);

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
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
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
      let currentEventType = 'token'; // Default event type

      setStreaming(true);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6));
              handleSSEEvent(currentEventType, parsed);
            } catch {
              // Skip malformed JSON
            }
            // Reset to default after processing data
            currentEventType = 'token';
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
  }, [addMessage, handleSSEEvent, clearAgentSteps, setLoading, setStreaming, getToken]);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    setStreaming(false);
    setLoading(false);
  }, [setStreaming, setLoading]);

  return { sendMessage, abort };
}

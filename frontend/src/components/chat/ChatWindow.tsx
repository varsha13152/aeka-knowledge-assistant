'use client';

/**
 * Main chat interface — streaming messages with agent step visualization.
 *
 * Features:
 * - SSE streaming display with typing indicator
 * - Source citations with expandable previews
 * - Agent activity sidebar
 * - Message history
 */

import { FormEvent, useRef, useState } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useSSE } from '@/hooks/useSSE';
import { StreamingMessage } from './StreamingMessage';
import { AgentSteps } from './AgentSteps';
import { MarkdownMessage } from './MarkdownMessage';

export function ChatWindow() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    activeAgentSteps,
    showAgentPanel,
    toggleAgentPanel,
  } = useChatStore();

  const { sendMessage, abort } = useSSE();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    sendMessage({ message: input.trim() });
    setInput('');
  };

  return (
    <div className="flex h-full">
      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <h2 className="text-2xl font-semibold text-gray-700">
                  Welcome to AEKA
                </h2>
                <p className="mt-2 text-gray-500">
                  Ask questions about your uploaded documents.
                  <br />
                  I'll search, synthesize, and cite my sources.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-brand-600 text-white'
                      : msg.role === 'system'
                      ? 'bg-red-50 text-red-700 border border-red-200'
                      : 'bg-white border border-gray-200 shadow-sm'
                  }`}
                >
                  <div className="prose-chat text-sm">
                    {msg.role === 'assistant' ? (
                      <MarkdownMessage content={msg.content} />
                    ) : (
                      <span className="whitespace-pre-wrap">{msg.content}</span>
                    )}
                  </div>
                  {msg.role === 'assistant' && msg.costUsd !== undefined && (
                    <div className="mt-2 flex items-center gap-3 border-t pt-2 text-xs text-gray-400">
                      <span>{msg.model}</span>
                      <span>{msg.latencyMs}ms</span>
                      <span>${msg.costUsd?.toFixed(4)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Streaming message */}
            {isStreaming && streamingContent && (
              <div className="flex justify-start">
                <StreamingMessage content={streamingContent} />
              </div>
            )}

            {/* Loading indicator */}
            {isLoading && !isStreaming && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 rounded-full bg-brand-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="h-2 w-2 rounded-full bg-brand-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="h-2 w-2 rounded-full bg-brand-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="border-t bg-white px-4 py-4">
          <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              disabled={isLoading}
            />
            {isStreaming ? (
              <button
                type="button"
                onClick={abort}
                className="rounded-xl bg-red-500 px-6 py-3 text-sm font-medium text-white hover:bg-red-600"
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="rounded-xl bg-brand-600 px-6 py-3 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Send
              </button>
            )}
            <button
              type="button"
              onClick={toggleAgentPanel}
              className={`rounded-xl border px-3 py-3 text-sm ${
                showAgentPanel ? 'border-brand-500 text-brand-600' : 'border-gray-300 text-gray-500'
              }`}
              title="Toggle agent activity panel"
            >
              🤖
            </button>
          </form>
        </div>
      </div>

      {/* Agent activity panel */}
      {showAgentPanel && (
        <div className="w-80 border-l bg-gray-50 overflow-y-auto">
          <AgentSteps steps={activeAgentSteps} />
        </div>
      )}
    </div>
  );
}

'use client';

/**
 * Session sidebar — list past conversations, create new ones.
 */

import { useCallback, useEffect } from 'react';
import { useChatStore, type ChatSession } from '@/stores/chatStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function SessionSidebar() {
  const { sessions, activeSessionId, setActiveSession, setSessions, reset } = useChatStore();

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/chat/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  }, [setSessions]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleNewChat = () => {
    setActiveSession(null);
    reset();
  };

  const handleSelectSession = async (session: ChatSession) => {
    setActiveSession(session.id);
    // Load messages for this session
    try {
      const res = await fetch(`${API_URL}/api/v1/chat/sessions/${session.id}/messages`);
      if (res.ok) {
        const messages = await res.json();
        // Update store with loaded messages
        reset();
        messages.forEach((msg: any) => {
          useChatStore.getState().addMessage({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            model: msg.model,
            latencyMs: msg.latency_ms,
            costUsd: msg.cost_usd,
            createdAt: msg.created_at,
          });
        });
      }
    } catch (err) {
      console.error('Failed to load session messages:', err);
    }
  };

  return (
    <div className="w-64 border-r bg-gray-50 flex flex-col h-full">
      <div className="p-3 border-b">
        <button
          onClick={handleNewChat}
          className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2"
        >
          <span>+</span> New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-0.5">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => handleSelectSession(session)}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm truncate ${
                activeSessionId === session.id
                  ? 'bg-brand-100 text-brand-800'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <p className="truncate font-medium">{session.title || 'Untitled'}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {new Date(session.createdAt).toLocaleDateString()}
              </p>
            </button>
          ))}

          {sessions.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">
              No conversations yet
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

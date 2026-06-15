/**
 * Chat state management with Zustand.
 *
 * Handles:
 * - Message history per session
 * - Streaming state (partial tokens)
 * - Agent step visualization
 * - Session management
 */

import { create } from 'zustand';

export interface Source {
  chunk_id: string;
  document_id: string;
  content_preview: string;
  score: number;
}

export interface AgentStep {
  node: string;
  action: string;
  timestamp?: string;
  [key: string]: any;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Source[];
  agentSteps?: AgentStep[];
  model?: string;
  latencyMs?: number;
  costUsd?: number;
  isStreaming?: boolean;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
}

interface ChatState {
  // Sessions
  sessions: ChatSession[];
  activeSessionId: string | null;

  // Messages
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  streamingContent: string;

  // Agent visualization
  activeAgentSteps: AgentStep[];
  showAgentPanel: boolean;

  // Actions
  setActiveSession: (sessionId: string | null) => void;
  addMessage: (message: Message) => void;
  updateStreamingContent: (content: string) => void;
  finalizeStreaming: (metadata: Record<string, any>) => void;
  addAgentStep: (step: AgentStep) => void;
  clearAgentSteps: () => void;
  setLoading: (loading: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  toggleAgentPanel: () => void;
  setSessions: (sessions: ChatSession[]) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isLoading: false,
  isStreaming: false,
  streamingContent: '',
  activeAgentSteps: [],
  showAgentPanel: true,

  setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateStreamingContent: (content) =>
    set((state) => ({
      streamingContent: state.streamingContent + content,
      isStreaming: true,
    })),

  finalizeStreaming: (metadata) =>
    set((state) => {
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: state.streamingContent,
        model: metadata.model,
        latencyMs: metadata.latency_ms,
        costUsd: metadata.cost_usd,
        agentSteps: [...state.activeAgentSteps],
        createdAt: new Date().toISOString(),
      };

      return {
        messages: [...state.messages, assistantMessage],
        streamingContent: '',
        isStreaming: false,
        isLoading: false,
      };
    }),

  addAgentStep: (step) =>
    set((state) => ({
      activeAgentSteps: [...state.activeAgentSteps, { ...step, timestamp: new Date().toISOString() }],
    })),

  clearAgentSteps: () => set({ activeAgentSteps: [] }),

  setLoading: (loading) => set({ isLoading: loading }),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  toggleAgentPanel: () => set((state) => ({ showAgentPanel: !state.showAgentPanel })),
  setSessions: (sessions) => set({ sessions }),

  reset: () =>
    set({
      messages: [],
      streamingContent: '',
      isStreaming: false,
      isLoading: false,
      activeAgentSteps: [],
    }),
}));

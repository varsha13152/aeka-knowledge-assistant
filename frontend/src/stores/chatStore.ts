/**
 * Chat state management with Zustand.
 *
 * Handles:
 * - Message history per session
 * - Streaming state (partial tokens)
 * - Agent step visualization
 * - Session management
 * - Document viewer state
 */

import { create } from 'zustand';

export interface Source {
  chunk_id: string;
  document_id: string;
  filename: string | null;
  content_type: string | null;
  content_preview: string;
  score: number;
  page_start: number | null;
  page_end: number | null;
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

export interface ActiveDocument {
  documentId: string;
  filename: string;
  contentType: string;
  page: number;
  highlightText: string;
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

  // Document viewer
  activeDocument: ActiveDocument | null;

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
  openDocumentViewer: (doc: ActiveDocument) => void;
  closeDocumentViewer: () => void;
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
  activeDocument: null,

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
      // Extract sources from agent steps
      const sourcesStep = state.activeAgentSteps.find(
        (s) => s.action === 'sources_retrieved'
      );
      const sources: Source[] = sourcesStep?.sources || [];

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: state.streamingContent,
        sources: sources.length > 0 ? sources : undefined,
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

  openDocumentViewer: (doc) => set({ activeDocument: doc }),
  closeDocumentViewer: () => set({ activeDocument: null }),

  reset: () =>
    set({
      messages: [],
      streamingContent: '',
      isStreaming: false,
      isLoading: false,
      activeAgentSteps: [],
      activeDocument: null,
    }),
}));

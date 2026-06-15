/**
 * WebSocket hook for real-time updates (HITL review queue, agent status).
 *
 * Features:
 * - Auto-reconnect with exponential backoff
 * - Typed message handling
 * - Connection state tracking
 */

import { useCallback, useEffect, useRef, useState } from 'react';

interface WebSocketOptions {
  url: string;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  autoReconnect?: boolean;
  maxRetries?: number;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useWebSocket(options: WebSocketOptions) {
  const { url, onMessage, onOpen, onClose, autoReconnect = true, maxRetries = 5 } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionState('connecting');
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnectionState('connected');
      retriesRef.current = 0;
      onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch {
        onMessage?.(event.data);
      }
    };

    ws.onclose = () => {
      setConnectionState('disconnected');
      onClose?.();

      // Auto-reconnect with exponential backoff
      if (autoReconnect && retriesRef.current < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 30000);
        retriesRef.current++;
        timeoutRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      setConnectionState('error');
    };

    wsRef.current = ws;
  }, [url, onMessage, onOpen, onClose, autoReconnect, maxRetries]);

  const disconnect = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionState('disconnected');
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connectionState, send, disconnect, reconnect: connect };
}

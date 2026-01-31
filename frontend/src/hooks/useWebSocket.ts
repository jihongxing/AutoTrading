import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { getAccessToken } from '@/api/client';

export type WSChannel = 'trading' | 'risk' | 'state' | 'market';
export type WSAction = 'update' | 'create' | 'delete' | 'snapshot';

export interface WSMessage {
  channel: WSChannel;
  type: string;
  action: WSAction;
  data: unknown;
  timestamp: string;
}

interface UseWebSocketOptions {
  onMessage?: (msg: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoConnect?: boolean;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// 全局单例 WebSocket
let globalWs: WebSocket | null = null;
let globalReconnectTimeout: number | undefined;
let globalReconnectAttempts = 0;
const messageHandlers = new Set<(msg: WSMessage) => void>();
const connectHandlers = new Set<() => void>();
const disconnectHandlers = new Set<() => void>();
let isGlobalConnected = false;
let currentToken = '';

function getGlobalConnection(token: string): WebSocket | null {
  if (globalWs?.readyState === WebSocket.OPEN) return globalWs;
  if (globalWs?.readyState === WebSocket.CONNECTING) return globalWs;
  
  if (!token) return null;
  currentToken = token;
  
  try {
    const url = `${WS_URL}/ws/all?token=${token}`;
    globalWs = new WebSocket(url);
    
    globalWs.onopen = () => {
      isGlobalConnected = true;
      globalReconnectAttempts = 0;
      connectHandlers.forEach(h => h());
    };
    
    globalWs.onclose = () => {
      isGlobalConnected = false;
      globalWs = null;
      disconnectHandlers.forEach(h => h());
      scheduleGlobalReconnect();
    };
    
    globalWs.onerror = () => {};
    
    globalWs.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        messageHandlers.forEach(h => h(msg));
      } catch {}
    };
    
    return globalWs;
  } catch {
    return null;
  }
}

function scheduleGlobalReconnect() {
  if (globalReconnectAttempts >= 5 || !currentToken) return;
  if (globalReconnectTimeout) clearTimeout(globalReconnectTimeout);
  
  const delay = Math.min(1000 * Math.pow(2, globalReconnectAttempts), 30000);
  globalReconnectAttempts++;
  
  globalReconnectTimeout = window.setTimeout(() => {
    getGlobalConnection(currentToken);
  }, delay);
}

function closeGlobalConnection() {
  if (globalReconnectTimeout) {
    clearTimeout(globalReconnectTimeout);
    globalReconnectTimeout = undefined;
  }
  if (globalWs) {
    globalWs.close();
    globalWs = null;
  }
  isGlobalConnected = false;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onMessage, onConnect, onDisconnect, autoConnect = true } = options;
  const [isConnected, setIsConnected] = useState(isGlobalConnected);
  const [error, setError] = useState<string | null>(null);
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
  }, [onMessage, onConnect, onDisconnect]);

  useEffect(() => {
    if (!autoConnect || !isAuthenticated) return;
    
    const token = getAccessToken();
    if (!token) return;

    const msgHandler = (msg: WSMessage) => onMessageRef.current?.(msg);
    const connHandler = () => {
      setIsConnected(true);
      setError(null);
      onConnectRef.current?.();
    };
    const disconnHandler = () => {
      setIsConnected(false);
      onDisconnectRef.current?.();
    };
    
    messageHandlers.add(msgHandler);
    connectHandlers.add(connHandler);
    disconnectHandlers.add(disconnHandler);
    
    getGlobalConnection(token);
    setIsConnected(isGlobalConnected);
    
    return () => {
      messageHandlers.delete(msgHandler);
      connectHandlers.delete(connHandler);
      disconnectHandlers.delete(disconnHandler);
      
      if (messageHandlers.size === 0) {
        closeGlobalConnection();
      }
    };
  }, [autoConnect, isAuthenticated]);

  const send = useCallback((data: object) => {
    if (globalWs?.readyState === WebSocket.OPEN) {
      globalWs.send(JSON.stringify(data));
    }
  }, []);

  return { isConnected, error, send };
}

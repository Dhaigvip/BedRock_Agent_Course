/**
 * useAgent — WebSocket hook for the Travel Concierge agent.
 *
 * Manages the WebSocket connection lifecycle, message state, and streaming.
 *
 * Usage:
 *   const { messages, toolEvents, isStreaming, sendMessage } = useAgent();
 *
 * The hook:
 *  1. Opens a WebSocket to ws://localhost:8100/ws/chat on mount.
 *  2. Re-connects automatically if the connection drops.
 *  3. Appends tokens to the last assistant message as they stream in
 *     (giving the "typewriter" effect in the UI).
 *  4. Collects tool_call / tool_result frames into toolEvents so the
 *     UI can show which tools were invoked.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import type { Message, ToolEvent, WsFrame } from "../types";

// ── Config ────────────────────────────────────────────────────────────────────

const WS_URL      = "ws://localhost:8100/ws/chat";
const RECONNECT_MS = 3_000;   // wait 3 s before reconnecting

// Persist a stable user_id across page reloads (stored in localStorage)
function getUserId(): string {
  const key = "travel_concierge_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `user_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(key, id);
  }
  return id;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAgent() {
  const [messages,   setMessages]   = useState<Message[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  const wsRef    = useRef<WebSocket | null>(null);
  const userId   = useRef(getUserId());
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Unique message id helper ────────────────────────────────────────────────
  const nextId = useCallback(() => `msg_${Date.now()}_${Math.random()}`, []);

  // ── Handle incoming WebSocket frames ────────────────────────────────────────
  const handleFrame = useCallback((frame: WsFrame) => {
    switch (frame.type) {

      case "token":
        // Append the token to the last assistant message (streaming)
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.isStreaming) {
            return [
              ...prev.slice(0, -1),
              { ...last, text: last.text + frame.text },
            ];
          }
          // No streaming message yet — create one
          return [
            ...prev,
            { id: nextId(), role: "assistant", text: frame.text, isStreaming: true },
          ];
        });
        break;

      case "tool_call":
        setToolEvents(prev => [...prev, { name: frame.name, input: frame.input }]);
        break;

      case "tool_result":
        // Merge result into the matching tool event
        setToolEvents(prev =>
          prev.map(te =>
            te.name === frame.name && te.result === undefined
              ? { ...te, result: frame.result }
              : te
          )
        );
        break;

      case "done":
        // Mark the last assistant message as finished
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [...prev.slice(0, -1), { ...last, isStreaming: false }];
          }
          return prev;
        });
        setIsStreaming(false);
        break;

      case "error":
        console.error("[agent] server error:", frame.message);
        setMessages(prev => [
          ...prev,
          {
            id:          nextId(),
            role:        "assistant",
            text:        `Error: ${frame.message}`,
            isStreaming: false,
          },
        ]);
        setIsStreaming(false);
        break;
    }
  }, [nextId]);

  // ── WebSocket lifecycle ─────────────────────────────────────────────────────
  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[ws] connected");
      setIsConnected(true);
      if (retryRef.current) clearTimeout(retryRef.current);
    };

    ws.onmessage = (ev: MessageEvent<string>) => {
      try {
        const frame: WsFrame = JSON.parse(ev.data);
        handleFrame(frame);
      } catch {
        console.error("[ws] bad JSON frame:", ev.data);
      }
    };

    ws.onclose = () => {
      console.log("[ws] disconnected — retrying in", RECONNECT_MS, "ms");
      setIsConnected(false);
      retryRef.current = setTimeout(connect, RECONNECT_MS);
    };

    ws.onerror = (err) => {
      console.error("[ws] error:", err);
      ws.close();   // triggers onclose -> reconnect
    };
  }, [handleFrame]);

  useEffect(() => {
    connect();
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // ── Public: send a message ──────────────────────────────────────────────────
  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn("[ws] not connected — message dropped");
      return;
    }
    if (isStreaming) return;   // one turn at a time

    // Add the user message to the UI immediately (optimistic update)
    setMessages(prev => [
      ...prev,
      { id: nextId(), role: "user", text, isStreaming: false },
    ]);
    setToolEvents([]);  // clear previous tool events for this turn
    setIsStreaming(true);

    wsRef.current.send(JSON.stringify({
      message: text,
      user_id: userId.current,
    }));
  }, [isStreaming, nextId]);

  return { messages, toolEvents, isStreaming, isConnected, sendMessage };
}

/**
 * ChatWindow — top-level chat container.
 *
 * Layout:
 *  ┌─────────────────────────────────────────────┐
 *  │  Header (title + connection badge)           │
 *  ├─────────────────────────────────────────────┤
 *  │  MessageList (scrollable, fills remaining)   │
 *  ├─────────────────────────────────────────────┤
 *  │  ToolPanel (visible only during tool use)    │
 *  ├─────────────────────────────────────────────┤
 *  │  InputBar (fixed at bottom)                  │
 *  └─────────────────────────────────────────────┘
 */

import { useAgent }     from "../hooks/useAgent";
import { MessageList }  from "./MessageList";
import { ToolPanel }    from "./ToolPanel";
import { InputBar }     from "./InputBar";

export function ChatWindow() {
  const { messages, toolEvents, isStreaming, isConnected, sendMessage } = useAgent();

  return (
    <div className="chat-window">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="chat-header">
        <div className="chat-title">
          <span className="chat-icon">✈️</span>
          Travel Concierge
        </div>
        <div className={`connection-badge ${isConnected ? "connected" : "disconnected"}`}>
          {isConnected ? "Connected" : "Reconnecting…"}
        </div>
      </header>

      {/* ── Messages ───────────────────────────────────────────────────────── */}
      <MessageList messages={messages} />

      {/* ── Tool events (only shown when tools were called) ─────────────────── */}
      <ToolPanel events={toolEvents} />

      {/* ── Input ──────────────────────────────────────────────────────────── */}
      <InputBar isDisabled={!isConnected || isStreaming} onSend={sendMessage} />

    </div>
  );
}

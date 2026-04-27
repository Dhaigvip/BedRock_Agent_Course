/**
 * MessageList — renders the chat history.
 *
 * User messages align right; assistant messages align left.
 * The last assistant message shows a blinking cursor while isStreaming=true.
 * Scrolls to the bottom automatically whenever messages change.
 */

import { useEffect, useRef } from "react";
import type { Message } from "../types";

interface Props {
  messages: Message[];
}

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <p className="placeholder">
          Ask me anything about your next trip ✈️
        </p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map(msg => (
        <div
          key={msg.id}
          className={`message ${msg.role} ${msg.isStreaming ? "streaming" : ""}`}
        >
          <div className="bubble">
            {msg.text}
            {msg.isStreaming && <span className="cursor" aria-hidden="true" />}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

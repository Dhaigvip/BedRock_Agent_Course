/**
 * InputBar — text field + send button at the bottom of the chat.
 *
 * Pressing Enter (without Shift) sends the message.
 * The button is disabled while a response is streaming.
 */

import { useState, useRef, type KeyboardEvent } from "react";

interface Props {
  isDisabled:  boolean;
  onSend:      (text: string) => void;
}

export function InputBar({ isDisabled, onSend }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isDisabled) return;
    onSend(trimmed);
    setText("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter alone = send; Shift+Enter = new line
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-grow the textarea up to ~6 lines
  const handleInput = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  };

  return (
    <div className="input-bar">
      <textarea
        ref={textareaRef}
        className="input-textarea"
        placeholder="Ask about destinations, weather, hotels…"
        value={text}
        disabled={isDisabled}
        rows={1}
        onChange={e => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
      />
      <button
        className="send-btn"
        onClick={handleSend}
        disabled={isDisabled || !text.trim()}
        aria-label="Send message"
      >
        {isDisabled ? (
          <span className="spinner" aria-label="Waiting for response" />
        ) : (
          // Paper-plane icon (inline SVG — no extra dep needed)
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
               width="20" height="20">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        )}
      </button>
    </div>
  );
}

/**
 * Shared types for the Travel Concierge chat UI.
 */

export type MessageRole = "user" | "assistant";

export interface Message {
  id:          string;
  role:        MessageRole;
  text:        string;
  isStreaming: boolean;   // true while tokens are still arriving
}

export interface ToolEvent {
  name:    string;
  input?:  Record<string, unknown>;
  result?: string;
}

// ── WebSocket frame shapes (Server -> Client) ─────────────────────────────────

export type WsFrame =
  | { type: "token";       text:    string }
  | { type: "tool_call";   name:    string; input:   Record<string, unknown> }
  | { type: "tool_result"; name:    string; result:  string }
  | { type: "done" }
  | { type: "error";       message: string };

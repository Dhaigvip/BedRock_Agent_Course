/**
 * ToolPanel — shows which MCP tools were called during the last turn.
 *
 * Each entry shows:
 *  - Tool name + input params
 *  - A spinner while the result is pending, then the first 200 chars of output
 *
 * Hidden when there are no tool events.
 */

import type { ToolEvent } from "../types";

interface Props {
  events: ToolEvent[];
}

export function ToolPanel({ events }: Props) {
  if (events.length === 0) return null;

  return (
    <div className="tool-panel">
      <h3 className="tool-panel-title">Tools used</h3>
      <ul className="tool-list">
        {events.map((te, i) => (
          <li key={i} className="tool-item">
            <span className="tool-name">{te.name}</span>
            {te.input && Object.keys(te.input).length > 0 && (
              <span className="tool-input">
                {Object.entries(te.input)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(", ")}
              </span>
            )}
            {te.result === undefined ? (
              <span className="tool-spinner" aria-label="running" />
            ) : (
              <span className="tool-result">{te.result.slice(0, 200)}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

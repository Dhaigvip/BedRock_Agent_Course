"""
Agent tracer — structured CloudWatch Logs for every node execution.

Each agent turn gets a short execution_id (8 hex chars) that ties all
log entries for that turn together. Every entry is a JSON object so
CloudWatch Insights can query by field.

Usage in a node:
    from tracer import log_event

    def classify_node(state):
        exec_id = new_execution_id()
        t0 = time.time()
        log_event(exec_id, "classify_start", {"user_text": text[:120]})
        ...
        log_event(exec_id, "classify_end", {"result": "complex", "latency_ms": elapsed_ms(t0)})
        return {"model_id": model_id, "execution_id": exec_id}

Environment variables (all optional — defaults work for local dev):
    CW_LOG_GROUP   CloudWatch log group name  (default: /travel-agent/dev)
    CW_LOG_STREAM  CloudWatch log stream name (default: agent)
    CW_ENABLED     Set to "false" to disable CloudWatch writes entirely
                   and fall back to stdout-only (useful for unit tests)
"""

import os
import json
import time
import uuid
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

_LOG_GROUP  = os.getenv("CW_LOG_GROUP",  "/travel-agent/dev")
_LOG_STREAM = os.getenv("CW_LOG_STREAM", "agent")
_ENABLED    = os.getenv("CW_ENABLED", "true").lower() != "false"
_region     = os.getenv("AWS_REGION", "us-east-1")

_cw: boto3.client = None          # lazy-initialised on first use
_sequence_token: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def new_execution_id() -> str:
    """Return a short 8-char hex ID for a single agent turn."""
    return uuid.uuid4().hex[:8]


def elapsed_ms(t0: float) -> int:
    """Return milliseconds elapsed since t0 (from time.time())."""
    return int((time.time() - t0) * 1000)


# ── Internal setup ────────────────────────────────────────────────────────────

def _get_client():
    global _cw
    if _cw is None:
        _cw = boto3.client("logs", region_name=_region)
    return _cw


def _ensure_log_group_and_stream():
    """Create log group + stream if they don't exist. Safe to call repeatedly."""
    cw = _get_client()
    try:
        cw.create_log_group(logGroupName=_LOG_GROUP)
    except cw.exceptions.ResourceAlreadyExistsException:
        pass
    except ClientError as e:
        print(f"[tracer] could not create log group: {e}")
        return

    try:
        cw.create_log_stream(logGroupName=_LOG_GROUP, logStreamName=_LOG_STREAM)
    except cw.exceptions.ResourceAlreadyExistsException:
        pass
    except ClientError as e:
        print(f"[tracer] could not create log stream: {e}")


_setup_done = False


def _ensure_setup():
    global _setup_done
    if not _setup_done:
        _ensure_log_group_and_stream()
        _setup_done = True


# ── Public API ────────────────────────────────────────────────────────────────

def log_event(execution_id: str, event: str, data: dict):
    """
    Write one structured log entry to CloudWatch Logs.

    The entry is always printed to stdout as well (for local dev visibility).
    If CloudWatch is unavailable or CW_ENABLED=false the function is non-fatal
    — the agent keeps running and the error is printed to stdout.

    Args:
        execution_id:  Short ID tying all events for one agent turn together.
                       Generate with new_execution_id() in classify_node.
        event:         Snake-case event name, e.g. "classify_start", "llm_end".
        data:          Arbitrary dict of fields to include in the log entry.
    """
    global _sequence_token

    entry = {
        "execution_id": execution_id,
        "event":        event,
        **data,
        "ts": time.time(),
    }

    # Always print locally — useful during development
    print(f"[trace] {execution_id} {event} {json.dumps(data)}")

    if not _ENABLED:
        return

    _ensure_setup()

    try:
        cw = _get_client()
        kwargs: dict = {
            "logGroupName":  _LOG_GROUP,
            "logStreamName": _LOG_STREAM,
            "logEvents": [{
                "timestamp": int(time.time() * 1000),
                "message":   json.dumps(entry),
            }],
        }
        if _sequence_token:
            kwargs["sequenceToken"] = _sequence_token

        response = cw.put_log_events(**kwargs)
        _sequence_token = response.get("nextSequenceToken")

    except ClientError as e:
        # Non-fatal — log and continue. Agent must not crash because of tracing.
        print(f"[tracer] CloudWatch write failed (non-fatal): {e.response['Error']['Message']}")
    except Exception as e:
        print(f"[tracer] unexpected tracer error (non-fatal): {e}")

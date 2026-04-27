import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

# ── Models ────────────────────────────────────────────────────────────────────

MODELS = {
    "simple":  "amazon.nova-micro-v1:0",   # fastest + cheapest — used for classification
    "complex": "amazon.nova-lite-v1:0",    # balanced — used for main reasoning
}

# Model ARN format required by the Knowledge Base RetrieveAndGenerate API
MODEL_ARNS = {
    "simple":  f"arn:aws:bedrock:{os.getenv('AWS_REGION', 'us-east-1')}::foundation-model/amazon.nova-micro-v1:0",
    "complex": f"arn:aws:bedrock:{os.getenv('AWS_REGION', 'us-east-1')}::foundation-model/amazon.nova-lite-v1:0",
}

# ── Clients ───────────────────────────────────────────────────────────────────

_region    = os.getenv("AWS_REGION", "us-east-1")
_client    = boto3.client("bedrock-runtime",       region_name=_region)
_kb_client = boto3.client("bedrock-agent-runtime", region_name=_region)
_bedrock   = boto3.client("bedrock",               region_name=_region)

# ── Token pricing (USD per 1000 tokens, as of 2024) ──────────────────────────
# Update these if AWS changes pricing: https://aws.amazon.com/bedrock/pricing/

_PRICING = {
    "amazon.nova-micro-v1:0": {"input": 0.000035, "output": 0.00014},
    "amazon.nova-lite-v1:0":  {"input": 0.00006,  "output": 0.00024},
}


def log_usage(model_id: str, usage: dict):
    """
    Log token counts and estimated cost for a single Bedrock Converse call.
    usage dict comes directly from response["usage"] returned by the API:
      {"inputTokens": int, "outputTokens": int, "totalTokens": int}
    """
    input_tokens  = usage.get("inputTokens",  0)
    output_tokens = usage.get("outputTokens", 0)

    pricing = _PRICING.get(model_id, {"input": 0, "output": 0})
    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

    print(
        f"[usage] {model_id.split('/')[-1]} | "
        f"in={input_tokens} out={output_tokens} | "
        f"cost=${cost:.6f}"
    )


# ── Converse API ──────────────────────────────────────────────────────────────

def call_bedrock(
    messages:     list[dict],
    tools:        list[dict] = [],
    model_id:     str        = MODELS["simple"],
    guardrail_id: str | None = None,
) -> dict:
    """
    Call an AWS Bedrock model via the Converse API.

    Args:
        messages:     Conversation history in Bedrock message format
        tools:        List of tool specs in Bedrock toolSpec format
        model_id:     Bedrock model ID — use MODELS["simple"] or MODELS["complex"]
        guardrail_id: Optional Bedrock Guardrail ID

    Returns:
        The assistant message dict from Bedrock
    """
    kwargs = {
        "modelId":  model_id,
        "messages": messages,
    }

    if tools:
        kwargs["toolConfig"] = {"tools": tools}

    if guardrail_id:
        kwargs["guardrailConfig"] = {
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion":    "DRAFT",
        }

    try:
        response = _client.converse(**kwargs)
    except ClientError as e:
        raise RuntimeError(f"Bedrock call failed: {e.response['Error']['Message']}") from e

    # Log token usage + cost after every call for traceability
    if "usage" in response:
        log_usage(model_id, response["usage"])

    return response["output"]["message"]


# ── Guardrails ────────────────────────────────────────────────────────────────

def get_or_create_guardrail(name: str = "travel-concierge-guardrail") -> str:
    """
    Return the guardrailId for the named guardrail, creating it if it doesn't
    exist yet. Safe to call on every startup — idempotent.

    The guardrail blocks:
      - Off-topic financial advice ("invest", "stock", "crypto")
      - Hate speech and violence (ContentPolicy)
      - PII in responses (masks email, phone, credit card numbers)

    Returns:
        The guardrail ID string (used in guardrailConfig when calling Bedrock)
    """
    # Check whether it already exists
    try:
        response = _bedrock.list_guardrails()
        for g in response.get("guardrails", []):
            if g["name"] == name:
                print(f"[guardrail] found existing: {g['id']}")
                return g["id"]
    except ClientError as e:
        raise RuntimeError(f"Could not list guardrails: {e.response['Error']['Message']}") from e

    # Create it
    try:
        response = _bedrock.create_guardrail(
            name=name,
            description="Travel Concierge — blocks off-topic and harmful content",
            topicPolicyConfig={
                "topicsConfig": [
                    {
                        "name":       "FinancialAdvice",
                        "definition": "Questions about investing, stocks, crypto, or financial planning.",
                        "examples":   [
                            "Should I invest my savings in Bitcoin?",
                            "What stocks should I buy before my trip?",
                        ],
                        "type": "DENY",
                    },
                ]
            },
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "HATE",      "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "VIOLENCE",  "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "SEXUAL",    "inputStrength": "HIGH", "outputStrength": "HIGH"},
                ]
            },
            sensitiveInformationPolicyConfig={
                "piiEntitiesConfig": [
                    {"type": "EMAIL",           "action": "ANONYMIZE"},
                    {"type": "PHONE",           "action": "ANONYMIZE"},
                    {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "ANONYMIZE"},
                ]
            },
            blockedInputMessaging=(
                "I'm a Travel Concierge and can only help with travel-related questions. "
                "For financial advice, please consult a qualified financial advisor."
            ),
            blockedOutputsMessaging=(
                "I can't provide that information. "
                "Let me know if you have any travel questions I can help with!"
            ),
        )
        guardrail_id = response["guardrailId"]
        print(f"[guardrail] created: {guardrail_id}")
        return guardrail_id

    except ClientError as e:
        raise RuntimeError(f"Could not create guardrail: {e.response['Error']['Message']}") from e


# ── Converse Stream API ───────────────────────────────────────────────────────

def call_bedrock_stream(
    messages:     list[dict],
    tools:        list[dict] = [],
    model_id:     str        = MODELS["simple"],
    guardrail_id: str | None = None,
):
    """
    Call Bedrock via the Converse *Stream* API and yield events as they arrive.

    This is a **synchronous generator** because boto3's converse_stream returns
    a synchronous event iterator.  In an asyncio context you can call it with:
        for event_type, data in call_bedrock_stream(...):
            ...
    For production workloads, wrap with asyncio.to_thread() to avoid briefly
    blocking the event loop on each network read.

    Yields tuples:
        ("token",      str)          — text chunk (send straight to client)
        ("tool_start", dict)         — {"toolUseId": str, "name": str}
        ("tool_input", str)          — raw JSON fragment for current tool
        ("tool_end",   None)         — tool input complete
        ("stop",       str)          — stop reason ("end_turn" | "tool_use")

    Tool input must be accumulated across ("tool_input", ...) events and
    parsed as JSON once "tool_end" fires.
    """
    kwargs = {
        "modelId":  model_id,
        "messages": messages,
    }

    if tools:
        kwargs["toolConfig"] = {"tools": tools}

    if guardrail_id:
        kwargs["guardrailConfig"] = {
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion":    "DRAFT",
        }

    try:
        response = _client.converse_stream(**kwargs)
    except ClientError as e:
        raise RuntimeError(f"Bedrock stream failed: {e.response['Error']['Message']}") from e

    for event in response["stream"]:

        # ── Text delta ──────────────────────────────────────────────────────
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"]["delta"]
            if "text" in delta:
                yield ("token", delta["text"])
            elif "toolUse" in delta:
                # Partial tool input JSON fragment
                yield ("tool_input", delta["toolUse"].get("input", ""))

        # ── Block started (new text block or new tool call) ─────────────────
        elif "contentBlockStart" in event:
            start = event["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                yield ("tool_start", {
                    "toolUseId": start["toolUse"]["toolUseId"],
                    "name":      start["toolUse"]["name"],
                })

        # ── Block finished ──────────────────────────────────────────────────
        elif "contentBlockStop" in event:
            yield ("tool_end", None)

        # ── Message stop ────────────────────────────────────────────────────
        elif "messageStop" in event:
            yield ("stop", event["messageStop"]["stopReason"])

        # ── Token usage (arrives in metadata event at the very end) ─────────
        elif "metadata" in event:
            if "usage" in event["metadata"]:
                log_usage(model_id, event["metadata"]["usage"])


# ── Knowledge Base — RetrieveAndGenerate API ──────────────────────────────────

def retrieve_and_generate(
    query:          str,
    kb_id:          str,
    model_id:       str = MODELS["complex"],
    max_results:    int = 5,
) -> dict:
    """
    Query a Bedrock Knowledge Base and generate a grounded answer.

    Uses the RetrieveAndGenerate API which:
      1. Embeds the query using Titan Embeddings V2
      2. Searches the vector store for the top-k relevant chunks
      3. Augments the prompt with those chunks
      4. Returns a grounded answer with source citations

    Args:
        query:       The user's question
        kb_id:       Bedrock Knowledge Base ID (from .env BEDROCK_KB_ID)
        model_id:    Model to use for generation (default: Nova Lite)
        max_results: Max number of document chunks to retrieve (default: 5)

    Returns:
        dict with keys:
          "answer"   — generated text answer
          "citations" — list of source chunks used (each has text + location)
    """
    model_arn = MODEL_ARNS.get(
        next((k for k, v in MODELS.items() if v == model_id), "complex"),
        MODEL_ARNS["complex"],
    )

    try:
        response = _kb_client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn":        model_arn,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": max_results,
                        }
                    },
                },
            },
        )
    except ClientError as e:
        raise RuntimeError(f"RAG call failed: {e.response['Error']['Message']}") from e

    answer = response["output"]["text"]

    citations = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            citations.append({
                "text":     ref["content"]["text"],
                "location": ref.get("location", {}),
            })

    return {"answer": answer, "citations": citations}

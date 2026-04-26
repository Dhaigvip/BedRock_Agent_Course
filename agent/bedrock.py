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

# ── Client ────────────────────────────────────────────────────────────────────

_client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

# ── Call ──────────────────────────────────────────────────────────────────────

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

    return response["output"]["message"]

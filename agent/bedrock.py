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

_region  = os.getenv("AWS_REGION", "us-east-1")
_client  = boto3.client("bedrock-runtime",       region_name=_region)
_kb_client = boto3.client("bedrock-agent-runtime", region_name=_region)

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

    return response["output"]["message"]


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

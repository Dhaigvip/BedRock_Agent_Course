"""
Upload travel guide documents to S3 and trigger a Knowledge Base sync.

Usage:
    cd rag-docs
    uv run --directory ../agent python upload_docs.py

Requirements in .env (agent/.env):
    AWS_REGION       = us-east-1
    S3_BUCKET_NAME   = your-bucket-name        (created in V7.4)
    BEDROCK_KB_ID    = your-knowledge-base-id  (created in V7.3)
    BEDROCK_DS_ID    = your-data-source-id     (shown in KB console)
"""

import os
import sys
import time
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the agent folder
load_dotenv(Path(__file__).parent.parent / "agent" / ".env")

REGION       = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME  = os.getenv("S3_BUCKET_NAME")
KB_ID        = os.getenv("BEDROCK_KB_ID")
DS_ID        = os.getenv("BEDROCK_DS_ID")

if not BUCKET_NAME:
    print("ERROR: S3_BUCKET_NAME not set in agent/.env")
    sys.exit(1)

DOCS_DIR = Path(__file__).parent

s3      = boto3.client("s3",                    region_name=REGION)
bedrock = boto3.client("bedrock-agent",         region_name=REGION)


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_documents():
    txt_files = sorted(DOCS_DIR.glob("*.txt"))
    if not txt_files:
        print("No .txt files found in rag-docs/")
        return

    print(f"Uploading {len(txt_files)} documents to s3://{BUCKET_NAME}/")
    for path in txt_files:
        key = f"travel-guides/{path.name}"
        s3.upload_file(
            Filename=str(path),
            Bucket=BUCKET_NAME,
            Key=key,
        )
        print(f"  uploaded: {key}")
    print("Upload complete.")


# ── Sync ──────────────────────────────────────────────────────────────────────

def start_ingestion():
    if not KB_ID or not DS_ID:
        print("\nSkipping KB sync — BEDROCK_KB_ID or BEDROCK_DS_ID not set in .env")
        print("Start the sync manually in the Bedrock console.")
        return

    print(f"\nStarting ingestion job for KB {KB_ID} / DS {DS_ID} ...")
    response = bedrock.start_ingestion_job(
        knowledgeBaseId=KB_ID,
        dataSourceId=DS_ID,
    )
    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"  Job ID: {job_id}")

    # Poll until complete
    while True:
        status_resp = bedrock.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DS_ID,
            ingestionJobId=job_id,
        )
        status = status_resp["ingestionJob"]["status"]
        print(f"  Status: {status}")
        if status in {"COMPLETE", "FAILED", "STOPPED"}:
            break
        time.sleep(5)

    if status == "COMPLETE":
        stats = status_resp["ingestionJob"].get("statistics", {})
        print(f"  Indexed: {stats.get('numberOfDocumentsScanned', '?')} documents")
        print("Ingestion complete. Knowledge Base is ready.")
    else:
        print(f"Ingestion ended with status: {status}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    upload_documents()
    start_ingestion()

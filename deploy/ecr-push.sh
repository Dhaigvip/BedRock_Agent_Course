#!/usr/bin/env bash
# ── Push Docker images to Amazon ECR ─────────────────────────────────────────
#
# Builds all four images and pushes them to ECR.
# Re-run whenever you want to deploy a new version.
#
# Prerequisites:
#   - AWS CLI v2 configured  (aws configure)
#   - Docker Desktop running
#
# Usage:
#   bash deploy/ecr-push.sh
#
# Override the WebSocket URL for the UI build (defaults to placeholder):
#   VITE_WS_URL=ws://your-alb-dns/ws/chat bash deploy/ecr-push.sh

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

SERVICES=("travel-api" "mcp-server" "agent-service")

echo ""
echo "==> Logging in to ECR  (account: ${AWS_ACCOUNT_ID}, region: ${AWS_REGION})"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_BASE"

# ── Create repos (idempotent — safe to run multiple times) ───────────────────
for svc in "${SERVICES[@]}"; do
  echo ""
  echo "==> Creating ECR repo: $svc"
  aws ecr create-repository \
    --repository-name "$svc" \
    --region "$AWS_REGION" \
    --image-scanning-configuration scanOnPush=true \
    2>/dev/null || echo "    (already exists — skipping)"
done

# ── Build and push travel-api ─────────────────────────────────────────────────
echo ""
echo "==> Building travel-api"
docker build -t travel-api ./travel-api
docker tag  travel-api:latest "${ECR_BASE}/travel-api:latest"
docker push "${ECR_BASE}/travel-api:latest"
echo "    Pushed: ${ECR_BASE}/travel-api:latest"

# ── Build and push mcp-server ─────────────────────────────────────────────────
echo ""
echo "==> Building mcp-server"
docker build -t mcp-server ./mcp-server
docker tag  mcp-server:latest "${ECR_BASE}/mcp-server:latest"
docker push "${ECR_BASE}/mcp-server:latest"
echo "    Pushed: ${ECR_BASE}/mcp-server:latest"

# ── Build and push agent-service ─────────────────────────────────────────────
echo ""
echo "==> Building agent-service"
docker build -t agent-service ./agent
docker tag  agent-service:latest "${ECR_BASE}/agent-service:latest"
docker push "${ECR_BASE}/agent-service:latest"
echo "    Pushed: ${ECR_BASE}/agent-service:latest"

echo ""
echo "============================================================"
echo "  All images pushed to ECR."
echo "  ECR base: ${ECR_BASE}"
echo ""
echo "  Next steps (in order):"
echo "  1. Deploy travel-api ECS service    (Step 7)"
echo "  2. Deploy mcp-server ECS service    (Step 8)"
echo "  3. Deploy agent-service ECS service (Step 9)"
echo "  4. Deploy React UI to S3            (Step 10)"
echo "     (UI is deployed via deploy-ui-s3.sh, not ECR)"
echo "============================================================"

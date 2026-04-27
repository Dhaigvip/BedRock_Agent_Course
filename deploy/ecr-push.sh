#!/usr/bin/env bash
# ── Push Docker images to Amazon ECR ─────────────────────────────────────────
#
# Run once to create ECR repos and push all images.
# After the first push, re-run whenever you want to deploy a new version.
#
# Prerequisites:
#   - AWS CLI v2 configured  (aws configure)
#   - Docker running
#   - AWS_REGION and AWS_ACCOUNT_ID set below (or exported in your shell)
#
# Usage:
#   bash deploy/ecr-push.sh

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

SERVICES=("travel-api" "agent-service" "travel-ui")

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

# ── Build and push agent-service ─────────────────────────────────────────────
# Build context is repo root — Dockerfile copies both agent/ and mcp-server/
echo ""
echo "==> Building agent-service"
docker build -f agent/Dockerfile -t agent-service .
docker tag  agent-service:latest "${ECR_BASE}/agent-service:latest"
docker push "${ECR_BASE}/agent-service:latest"
echo "    Pushed: ${ECR_BASE}/agent-service:latest"

# ── Build and push travel-ui ─────────────────────────────────────────────────
# Pass the real WebSocket URL (your ALB DNS name) as a build arg.
# Replace the placeholder with the ALB URL from your ECS service (V10.5).
echo ""
echo "==> Building travel-ui"
WS_URL="${VITE_WS_URL:-wss://REPLACE_WITH_YOUR_ALB_DNS/ws/chat}"
docker build \
  --build-arg "VITE_WS_URL=${WS_URL}" \
  -t travel-ui \
  ./ui
docker tag  travel-ui:latest "${ECR_BASE}/travel-ui:latest"
docker push "${ECR_BASE}/travel-ui:latest"
echo "    Pushed: ${ECR_BASE}/travel-ui:latest"

echo ""
echo "All images pushed to ECR."
echo "ECR base: ${ECR_BASE}"
echo ""
echo "Next step: create ECS task definitions (see deploy/task-def-travel-api.json"
echo "           and deploy/task-def-agent.json) then create Fargate services."

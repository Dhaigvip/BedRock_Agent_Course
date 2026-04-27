#!/usr/bin/env bash
# ── Deploy React UI to S3 + CloudFront ───────────────────────────────────────
#
# Run after creating your S3 bucket and CloudFront distribution in the console.
# See Section 10.6 of the course for the console walkthrough.
#
# Prerequisites:
#   - S3 bucket created with static website hosting disabled
#     (CloudFront will be the public entry point, not S3 directly)
#   - CloudFront distribution pointing to the S3 bucket (OAC or OAI)
#   - VITE_WS_URL set to your agent ALB DNS (wss://...)
#
# Usage:
#   VITE_WS_URL=wss://your-alb.amazonaws.com/ws/chat \
#   S3_BUCKET=your-bucket-name \
#   CF_DISTRIBUTION_ID=EXXXXXXXX \
#   bash deploy/deploy-ui-s3.sh

set -euo pipefail

S3_BUCKET="${S3_BUCKET:-REPLACE_WITH_YOUR_BUCKET_NAME}"
CF_DISTRIBUTION_ID="${CF_DISTRIBUTION_ID:-REPLACE_WITH_YOUR_CF_DISTRIBUTION_ID}"
WS_URL="${VITE_WS_URL:-wss://REPLACE_WITH_YOUR_ALB_DNS/ws/chat}"

echo ""
echo "==> Building UI  (VITE_WS_URL=${WS_URL})"
cd ui
VITE_WS_URL="$WS_URL" npm run build
cd ..

echo ""
echo "==> Syncing dist/ to s3://${S3_BUCKET}"
aws s3 sync ui/dist/ "s3://${S3_BUCKET}/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"

# index.html gets a short cache so users always get the latest
aws s3 cp ui/dist/index.html "s3://${S3_BUCKET}/index.html" \
  --cache-control "no-cache"

echo ""
echo "==> Invalidating CloudFront cache  (distribution: ${CF_DISTRIBUTION_ID})"
aws cloudfront create-invalidation \
  --distribution-id "$CF_DISTRIBUTION_ID" \
  --paths "/*"

echo ""
echo "Deploy complete."
echo "Your app is live at your CloudFront distribution URL."

#!/usr/bin/env bash
# ── Deploy React UI to S3 + CloudFront ───────────────────────────────────────
#
# Run after Step 10a (create ui/.env.production with your ALB WebSocket URL).
#
# Prerequisites:
#   1. ui/.env.production created with:
#        VITE_WS_URL=ws://your-alb.amazonaws.com/ws/chat
#   2. S3 bucket created (Step 10b)
#   3. CloudFront distribution created and pointing to the S3 bucket (Step 10c/10d)
#
# Usage:
#   S3_BUCKET=your-bucket-name \
#   CF_DISTRIBUTION_ID=EXXXXXXXX \
#   bash deploy/deploy-ui-s3.sh

set -euo pipefail

S3_BUCKET="${S3_BUCKET:-REPLACE_WITH_YOUR_BUCKET_NAME}"
CF_DISTRIBUTION_ID="${CF_DISTRIBUTION_ID:-REPLACE_WITH_YOUR_CF_DISTRIBUTION_ID}"

# Vite automatically picks up ui/.env.production during npm run build
echo ""
echo "==> Building UI (reads VITE_WS_URL from ui/.env.production)"
cd ui
npm run build
cd ..

echo ""
echo "==> Syncing dist/ to s3://${S3_BUCKET}"
aws s3 sync ui/dist/ "s3://${S3_BUCKET}/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"

# index.html gets no-cache so users always get the latest version
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

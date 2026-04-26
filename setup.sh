#!/usr/bin/env bash
# Install dependencies for all three sub-projects.
# Run once after cloning: bash setup.sh

set -e

echo ""
echo "==> travel-api"
(cd travel-api && uv sync)

echo ""
echo "==> mcp-server"
(cd mcp-server && uv sync)

echo ""
echo "==> agent"
(cd agent && uv sync)

echo ""
echo "All done. See README.md for how to run the stack."

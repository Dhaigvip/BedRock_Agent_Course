# ── React UI — Docker image ───────────────────────────────────────────────────
#
# Two-stage build:
#   Stage 1 (build)  — Node 20 runs "npm run build" -> produces dist/
#   Stage 2 (serve)  — nginx alpine serves the static files
#
# The final image is tiny (~25 MB) because it contains only nginx + static files,
# not Node, npm, or any JavaScript tooling.
#
# Build:
#   docker build -t travel-ui ./ui
#
# Build with custom agent URL (for AWS deployment):
#   docker build --build-arg VITE_WS_URL=wss://your-alb.amazonaws.com/ws/chat \
#                -t travel-ui ./ui
#
# Run (local):
#   docker run -p 8080:80 travel-ui
#   Open http://localhost:8080

# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Layer: install deps (cached unless package.json changes)
COPY package*.json .
RUN npm ci

# Optionally override the WebSocket URL at build time
ARG VITE_WS_URL=ws://localhost:8100/ws/chat
ENV VITE_WS_URL=$VITE_WS_URL

# Layer: copy source and build
COPY . .
RUN npm run build
# Output is in /app/dist/

# ── Stage 2: serve ────────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

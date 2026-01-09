# WebSocket Server Dockerfile
# Bun-based WebSocket server for real-time communication
# Build context: project root

FROM oven/bun:1-alpine AS base
WORKDIR /workspace

# Install dependencies - preserve directory structure for file: dependencies
FROM base AS deps
# Copy packages first (for file: dependencies)
COPY packages ./packages
# Copy web app package files
COPY apps/web/package.json apps/web/bun.lockb* ./apps/web/
WORKDIR /workspace/apps/web
RUN bun install --frozen-lockfile --production 2>/dev/null || bun install --production

# Build stage
FROM base AS builder
COPY --from=deps /workspace/packages ./packages
COPY --from=deps /workspace/apps/web/node_modules ./apps/web/node_modules
COPY apps/web/server ./apps/web/server
COPY apps/web/package.json ./apps/web/

# Runtime
FROM base AS runner
WORKDIR /workspace/apps/web

ENV NODE_ENV=production
ENV WS_PORT=8284

# Copy only what's needed for the WebSocket server
COPY --from=builder /workspace/packages ./../../packages
COPY --from=builder /workspace/apps/web/node_modules ./node_modules
COPY --from=builder /workspace/apps/web/server ./server
COPY --from=builder /workspace/apps/web/package.json ./

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 wsuser
USER wsuser

EXPOSE 8284

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8284/health || exit 1

CMD ["bun", "run", "server/ws-server.ts"]

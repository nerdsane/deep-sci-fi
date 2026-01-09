# WebSocket Server Dockerfile
# Bun-based WebSocket server for real-time communication
# Build context: project root

FROM oven/bun:1-alpine AS base
WORKDIR /app

# Install dependencies
FROM base AS deps
COPY apps/web/package.json ./
COPY apps/web/bun.lockb* ./
RUN bun install --frozen-lockfile --production 2>/dev/null || bun install --production

# Build stage (if needed)
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/server ./server
COPY apps/web/package.json ./

# Runtime
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV WS_PORT=8284

# Copy only what's needed for the WebSocket server
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/server ./server
COPY --from=builder /app/package.json ./

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 wsuser
USER wsuser

EXPOSE 8284

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8284/health || exit 1

CMD ["bun", "run", "server/ws-server.ts"]

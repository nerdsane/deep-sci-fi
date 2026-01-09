# Letta UI - Observability Dashboard
FROM oven/bun:1-alpine AS base

WORKDIR /app

# Install dependencies
FROM base AS deps
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Production image
FROM base AS runner
WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules

# Copy source files
COPY package.json ./
COPY src ./src
COPY tsconfig.json ./
COPY tailwind.config.js postcss.config.js ./

# Environment variables
ENV PORT=4000
ENV LETTA_BASE_URL=http://localhost:8283

EXPOSE 4000

# Run with bun
CMD ["bun", "run", "src/server.ts"]

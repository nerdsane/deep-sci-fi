# Web App - Next.js Chat + Canvas UI
# Build context: project root (for monorepo workspace packages)
# Note: Using Debian slim instead of Alpine for Prisma compatibility
FROM node:20-slim AS base
WORKDIR /workspace

# Install dependencies only when needed
FROM base AS deps
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# Copy ALL package files first
COPY packages ./packages
COPY apps/web/package.json ./apps/web/

# Install dependencies for workspace packages first
WORKDIR /workspace/packages/db
RUN npm install --production=false && npx prisma generate

WORKDIR /workspace/packages/types
RUN npm install --production=false || true

WORKDIR /workspace/packages/letta
RUN npm install --production=false

# Now install web app dependencies
WORKDIR /workspace/apps/web
RUN npm install

# Build the application
FROM base AS builder
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*
# Copy packages WITH their node_modules (for @prisma/client etc)
COPY --from=deps /workspace/packages ./packages
COPY --from=deps /workspace/apps/web/node_modules ./apps/web/node_modules
COPY apps/web ./apps/web
WORKDIR /workspace/apps/web

# Set environment for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm run build

# Production image
FROM node:20-slim AS runner
WORKDIR /app
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN groupadd --system --gid 1001 nodejs
RUN useradd --system --uid 1001 --gid nodejs nextjs

# Copy built assets from standalone output
COPY --from=builder /workspace/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/static ./.next/static

# Copy Prisma engine files for standalone build
COPY --from=builder /workspace/packages/db/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /workspace/packages/db/node_modules/@prisma ./node_modules/@prisma

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]

# Web App - Next.js Chat + Canvas UI
# Build context: project root (for monorepo workspace packages)
FROM node:20-alpine AS base
WORKDIR /workspace

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat

# Copy packages first (for file: dependencies)
COPY packages ./packages
# Copy web app package files
COPY apps/web/package.json ./apps/web/
WORKDIR /workspace/apps/web
RUN npm install

# Build the application
FROM base AS builder
COPY --from=deps /workspace/packages ./packages
COPY --from=deps /workspace/apps/web/node_modules ./apps/web/node_modules
COPY apps/web ./apps/web
WORKDIR /workspace/apps/web

# Set environment for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built assets from standalone output
COPY --from=builder /workspace/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]

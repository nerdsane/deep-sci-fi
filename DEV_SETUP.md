# Deep Sci-Fi - Development Setup

## Prerequisites

- **Node.js** 20+ (for Next.js app)
- **Bun** 1.0+ (for letta-code)
- **Docker** & **Docker Compose** (for PostgreSQL)
- **Git**

## Quick Start

### 1. Clone and Install

```bash
# Clone repository
git clone https://github.com/nerdsane/deep-sci-fi.git
cd deep-sci-fi

# Install Next.js app dependencies
cd apps/web
npm install  # or bun install

# Install database package dependencies
cd ../../packages/db
npm install  # or bun install
```

### 2. Start PostgreSQL Database

```bash
# From root directory
docker-compose -f docker-compose.dev.yml up -d

# Wait for database to be ready (health check)
# Check logs: docker-compose -f docker-compose.dev.yml logs -f postgres
```

### 3. Set Up Environment Variables

```bash
# Copy example env file
cd apps/web
cp .env.example .env

# Edit .env and configure:
# - DATABASE_URL (already set for local docker)
# - NEXTAUTH_SECRET (generate random string)
# - GOOGLE_CLIENT_ID/SECRET (optional, for OAuth)
# - LETTA_BASE_URL (set to your Letta server)
# - ANTHROPIC_API_KEY (for agents)
```

Generate NEXTAUTH_SECRET:
```bash
openssl rand -base64 32
```

### 4. Run Database Migrations

```bash
cd packages/db
npx prisma generate
npx prisma db push  # Push schema to database

# Optional: Open Prisma Studio to view database
npx prisma studio
```

### 5. Start Development Server

```bash
cd apps/web
npm run dev  # or bun dev

# App will be available at http://localhost:3000
```

## Project Structure

```
deep-sci-fi/
├── apps/
│   └── web/                 # Next.js web app
│       ├── app/             # Next.js 14 App Router
│       ├── components/      # React components (to be migrated from letta-code)
│       ├── lib/             # Utilities (auth, trpc, storage)
│       └── server/          # tRPC routers
│
├── packages/
│   ├── db/                  # Prisma schema & client
│   ├── types/               # Shared TypeScript types (to be added)
│   └── letta/               # Letta SDK wrapper (to be added)
│
├── letta/                   # Letta server (submodule)
├── letta-code/              # CLI tool (will be partially migrated)
├── letta-ui/                # Letta dashboard (separate from Canvas)
│
├── docs/                    # Documentation
│   ├── MIGRATION_PLAN.md
│   ├── AGENT_CONTEXT_SHARING.md
│   ├── CHAT_UI_INTEGRATION.md
│   └── IMMERSIVE_EXPERIENCES.md
│
└── docker-compose.dev.yml   # Local PostgreSQL + Redis
```

## Development Workflow

### Database Changes

```bash
# 1. Edit packages/db/prisma/schema.prisma
# 2. Generate Prisma client
cd packages/db
npx prisma generate

# 3. Push changes to database
npx prisma db push

# 4. (Optional) Create migration
npx prisma migrate dev --name your_migration_name
```

### Adding tRPC Endpoints

1. Create/edit router in `apps/web/server/routers/`
2. Export from `apps/web/server/routers/index.ts`
3. Use in components via `trpc` hook

Example:
```typescript
// In component
import { trpc } from '@/lib/trpc';

function MyComponent() {
  const { data: worlds } = trpc.worlds.list.useQuery();
  // ...
}
```

### Running Letta Server (for agents)

```bash
# Start Letta server (from letta submodule)
cd letta
docker-compose -f dev-compose.yaml up -d

# Server will be available at http://localhost:8283
```

## Available Scripts

### Web App (`apps/web/`)
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript check

### Database (`packages/db/`)
- `npm run db:generate` - Generate Prisma client
- `npm run db:push` - Push schema to database
- `npm run db:migrate` - Create migration
- `npm run db:studio` - Open Prisma Studio

## Environment Variables

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `NEXTAUTH_SECRET` - Random secret for NextAuth.js
- `NEXTAUTH_URL` - App URL (http://localhost:3000 for dev)

### Optional
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth secret
- `LETTA_BASE_URL` - Letta server URL (default: http://localhost:8283)
- `ANTHROPIC_API_KEY` - For Claude agents
- `GOOGLE_API_KEY` - For Gemini image generation
- `OPENAI_API_KEY` - For DALL-E image generation

### AWS (to be configured later)
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (e.g., us-east-1)
- `AWS_S3_BUCKET` - S3 bucket name

## Troubleshooting

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.dev.yml ps

# Check logs
docker-compose -f docker-compose.dev.yml logs postgres

# Restart database
docker-compose -f docker-compose.dev.yml restart postgres
```

### Prisma Client Not Found
```bash
cd packages/db
npx prisma generate
```

### Port Already in Use
```bash
# Find process using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>
```

## Next Steps

See [docs/MIGRATION_PLAN.md](./docs/MIGRATION_PLAN.md) for the full migration roadmap.

Current phase: **Foundation** ✅
- Database schema
- Authentication
- tRPC API
- Basic Next.js app

Next phase: **Canvas Migration**
- Migrate visual novel components
- Migrate agent-driven UI components
- Set up asset storage (AWS S3)
- Create chat panel UI

# Deep Sci-Fi Migration Status

**Last Updated:** 2026-01-08
**Status:** ✅ READY TO RUN LOCALLY

---

## ✅ What's Been Completed

### Phase 1: Foundation (100%)
- ✅ Database schema (Prisma)
- ✅ Authentication (NextAuth)
- ✅ tRPC API layer
- ✅ Basic UI components

### Phase 2A: Two-Tier Agent Architecture (100%)
- ✅ User Agent (Orchestrator) - one per user
- ✅ World Agents - one per world
- ✅ Agent routing logic
- ✅ Memory block system

### Phase 2A-SDK: Letta SDK Integration (100%)
- ✅ @letta-ai/letta-client integration
- ✅ Client-side tool execution
- ✅ Approval handling loop
- ✅ Streaming support
- ✅ Tool implementations:
  - `world_draft_generator` ✅
  - `world_manager` ✅
  - `story_manager` ✅
  - `list_worlds` ✅
  - `user_preferences` ✅

### Phase 2B: UI Integration (100%)
- ✅ ChatPanel components
- ✅ World detail page
- ✅ Story detail page
- ✅ VisualNovelReader integration

### Phase 2C: UI Redesign (100%)
- ✅ Persistent chat sidebar (left)
- ✅ Canvas area (right)
- ✅ Agent switching with system messages
- ✅ Hybrid navigation
- ✅ Zustand state management

---

## 🚀 How to Run Locally

### Prerequisites
- ✅ Node.js 18+
- ✅ PostgreSQL 14+ with pgvector
- ✅ Docker (for Letta server)
- ✅ Anthropic API key

### Step-by-Step Setup

#### 1. Install Dependencies
```bash
cd apps/web
npm install --legacy-peer-deps
```

**Why `--legacy-peer-deps`?**
There's a peer dependency conflict between tRPC and React Query versions. This flag resolves it safely.

#### 2. Start PostgreSQL
```bash
# Option A: Docker (recommended)
docker run -d \
  --name deep-sci-fi-postgres \
  -e POSTGRES_USER=deepscifi \
  -e POSTGRES_PASSWORD=dev_password \
  -e POSTGRES_DB=deep_sci_fi_dev \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Option B: Use existing PostgreSQL
# Just ensure it's running on localhost:5432
```

#### 3. Start Letta Server
```bash
cd letta
docker-compose up -d

# Verify it's running
curl http://localhost:8283/health
```

**Note:** You do NOT need a Letta API key for local development! The orchestrator detects localhost and skips API key validation.

#### 4. Setup Database
```bash
cd packages/db
npx prisma db push
npx prisma generate
```

#### 5. Configure Environment
```bash
cd apps/web
cp .env.example .env
```

Edit `.env`:
```bash
# Database
DATABASE_URL="postgresql://deepscifi:dev_password@localhost:5432/deep_sci_fi_dev"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="<generate with: openssl rand -base64 32>"

# Letta Server (NO API KEY NEEDED FOR LOCALHOST!)
LETTA_BASE_URL="http://localhost:8283"
LETTA_API_KEY=""  # Leave empty for local dev

# Anthropic API (REQUIRED for world_draft_generator tool)
ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Google OAuth (optional)
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
```

#### 6. Start the App
```bash
cd apps/web
npm run dev
```

**Open:** http://localhost:3000

---

## ✅ What Should Work

### User Flow
1. **Sign up** with email/password
2. **Create a world** via chat or form
   - Chat: "I want to create a world about post-scarcity society"
   - Agent generates 3 world draft concepts
   - Click one to create the world
3. **Navigate to world** - World Agent loads, system message appears
4. **Create a story** via chat
   - "I want to write a story about a judge"
   - Agent creates story
5. **Navigate to story** - Story context set in World Agent
6. **Continue writing** - Agent generates story segments

### Features That Work
- ✅ Persistent chat sidebar on all pages
- ✅ Agent switching (User Agent ↔ World Agent)
- ✅ System messages show agent transitions
- ✅ Navigation commands ("show my worlds", "go back")
- ✅ Traditional clicking (world cards, story cards)
- ✅ World draft generation (uses Anthropic API)
- ✅ World management (save/load/update)
- ✅ Story creation and management
- ✅ VisualNovelReader for story display

---

## ⚠️ Known Limitations

### Not Yet Implemented
1. **Chat history persistence** - Messages are lost on page refresh (stored in Zustand, not database)
2. **Streaming responses** - Waits for full response (backend supports streaming, UI doesn't yet)
3. **Image generation** - `image_generator` tool not implemented
4. **Canvas UI** - `canvas_ui` tool for agent-created components not implemented
5. **Proactive suggestions** - `send_suggestion` tool not implemented
6. **Google OAuth** - Requires credentials setup
7. **AWS S3 uploads** - Requires credentials setup

### Possible Issues
1. **First-time load might be slow** - Letta server needs to warm up
2. **Agent creation takes ~5-10 seconds** - Normal for first-time setup
3. **World draft generation requires Anthropic API key** - Won't work without it

---

## 🐛 Troubleshooting

### "Cannot find module 'zustand'"
```bash
cd apps/web
npm install zustand --legacy-peer-deps
```

### "LETTA_API_KEY is required"
- Make sure `LETTA_BASE_URL=http://localhost:8283` in `.env`
- The orchestrator should detect localhost and skip API key check
- If error persists, check packages/letta/orchestrator.ts:47

### "Database connection failed"
```bash
# Test connection
psql -U deepscifi -d deep_sci_fi_dev -c "SELECT 1;"

# Check DATABASE_URL in .env matches your PostgreSQL setup
```

### "Letta server not responding"
```bash
cd letta
docker-compose logs -f letta-server

# Restart if needed
docker-compose restart letta-server
```

### "ANTHROPIC_API_KEY is required"
- Get API key from https://console.anthropic.com/
- Add to `.env`: `ANTHROPIC_API_KEY="sk-ant-..."`
- Only needed for `world_draft_generator` tool

### "Agent not responding"
- Check browser console for errors
- Check Letta server logs: `cd letta && docker-compose logs -f`
- Verify tRPC endpoints are working: http://localhost:3000/api/trpc/health

### "Chat not visible / Layout broken"
- Clear browser cache
- Check for console errors
- Verify layout.css is loaded

---

## 📊 File Structure

```
deep-sci-fi/
├── letta/                           # Letta server (Docker)
├── letta-code/                      # Original CLI (submodule)
├── apps/web/                        # Next.js web app
│   ├── app/
│   │   ├── layout.tsx               # ✨ Wraps with AppShell
│   │   ├── worlds/
│   │   │   ├── page.tsx             # ✨ Full-width, no ChatPanel
│   │   │   └── [worldId]/
│   │   │       ├── page.tsx         # ✨ Full-width, no ChatPanel
│   │   │       └── stories/[storyId]/
│   │   │           └── page.tsx     # ✨ Full-width, no ChatPanel
│   ├── components/
│   │   ├── layout/                  # ✨ NEW
│   │   │   ├── AppShell.tsx         # ✨ NEW - Main layout wrapper
│   │   │   ├── PersistentChatSidebar.tsx  # ✨ NEW - Left sidebar
│   │   │   └── layout.css           # ✨ NEW - Grid layout
│   │   └── chat/
│   │       ├── ChatPanel.tsx        # Existing (updated)
│   │       ├── Message.tsx          # ✨ Updated for individual props
│   │       ├── ChatInput.tsx        # Existing
│   │       └── ChatPanelContainer.tsx  # ❌ DELETED
│   └── lib/
│       ├── chat-store.ts            # ✨ NEW - Zustand store
│       └── use-navigation-context.ts # ✨ NEW - URL context hook
├── packages/
│   ├── letta/
│   │   ├── orchestrator.ts          # ✨ Updated - API key optional
│   │   ├── tools/                   # Client-side tools
│   │   │   ├── world_draft_generator.ts  # ✅ Implemented
│   │   │   ├── world_manager.ts          # ✅ Implemented
│   │   │   └── story_manager.ts          # ✅ Implemented
│   │   └── memory/                  # Memory block system
│   └── db/
│       └── prisma/schema.prisma     # Database schema
└── LOCAL_SETUP.md                   # Detailed setup guide
```

---

## 🎯 Next Steps (Optional Enhancements)

1. **Chat history persistence** - Save messages to database
2. **Streaming UI** - Show agent responses incrementally
3. **Image generation** - Implement `image_generator` tool
4. **Canvas UI** - Implement `canvas_ui` for dynamic components
5. **Better mobile layout** - Tabbed interface for small screens
6. **Search chat history** - Find previous messages
7. **Export conversations** - Download chat as markdown

---

## ✅ Ready to Run Checklist

- [ ] PostgreSQL running on localhost:5432
- [ ] Letta server running on localhost:8283
- [ ] Dependencies installed (`npm install --legacy-peer-deps`)
- [ ] Database schema pushed (`npx prisma db push`)
- [ ] `.env` configured with valid values
- [ ] Anthropic API key added to `.env`
- [ ] Web app started (`npm run dev`)
- [ ] Can access http://localhost:3000

**If all boxes checked → YOU'RE READY TO GO! 🚀**

---

## 📝 Testing Checklist

Once running, test these flows:

- [ ] Sign up with email/password
- [ ] Chat appears on left sidebar
- [ ] User Agent shows "Welcome!" message
- [ ] Create world via chat ("I want to create a world about X")
- [ ] Agent generates world drafts (3 cards)
- [ ] Click draft → creates world → navigates to world page
- [ ] System message: "Switching to World Agent for [name]"
- [ ] Create story via chat ("I want to write a story about Y")
- [ ] Navigate to story page
- [ ] Story context set in World Agent
- [ ] Continue story via chat
- [ ] Navigation commands work ("show my worlds", "go back")
- [ ] Chat persists across all navigation
- [ ] Click world/story cards → canvas updates, chat stays

---

**Status:** All core features implemented and ready to run!
**Last Commit:** bf6bd5d (feat: Implement persistent chat sidebar with hybrid navigation)

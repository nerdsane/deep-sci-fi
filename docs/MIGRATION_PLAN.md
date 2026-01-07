# Deep Sci-Fi: Multi-User Migration Plan

**Status:** Planning
**Version:** 1.1
**Last Updated:** 2026-01-07

⭐ **UPDATE:** Added immersive experience features (visual novel, agent-driven UI, audio). See [IMMERSIVE_EXPERIENCES.md](./IMMERSIVE_EXPERIENCES.md) for details.

---

## 🎯 Migration Goals

Transform Deep Sci-Fi from a local, single-user CLI tool into a multi-user, browser-based web application while:

✅ **Preserving existing features:**
- Canvas UI (styling, layout, components)
- Agent capabilities (world/story management, image generation, evaluation)
- Immersive story reading experience
- Real-time updates via WebSocket

✅ **Adding new capabilities:**
- Multi-user authentication (email/password + Gmail OAuth)
- Database storage for worlds/stories
- Agent context sharing (World → Story)
- Responsive design (laptop + mobile)
- Object storage for assets

⏳ **Future enhancements:**
- Real-time collaboration
- Comments, annotations
- Version history UI
- Monetization

---

## 🏗️ Current Architecture

```
User (CLI)
    ↓
letta-code (TypeScript/Bun)
    ├── CLI/TUI interface
    ├── Canvas Gallery (React) [Port 3030]
    ├── Agent Bus (WebSocket) [Port 8284]
    └── Tools (world_manager, story_manager)
    ↓
Letta Server (Docker) [Port 8283]
    ├── Agent execution
    ├── Evaluation tools
    └── LLM calls
    ↓
File Storage (.dsf/)
    ├── worlds/*.json
    ├── stories/*/
    └── assets/
```

---

## 🎨 Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Browser (Laptop + Mobile)                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Canvas UI (Migrated from current)              │   │
│  │  ├── World Explorer                             │   │
│  │  ├── Story Reader                               │   │
│  │  └── Chat Panel (NEW - integrated Cmd+K input) │   │
│  └─────────────────────────────────────────────────┘   │
│            ↕ HTTPS/WSS                                  │
└─────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────┐
│                 API Gateway                            │
│         (Next.js App Router + tRPC)                    │
│  ├── Authentication (NextAuth.js)                     │
│  ├── Rate limiting                                     │
│  ├── WebSocket proxy                                   │
│  └── Static asset serving                              │
└─────────────────────┬─────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
┌────────▼────┐ ┌────▼─────┐ ┌───▼──────┐
│   World     │ │  Story   │ │   Auth   │
│  Service    │ │ Service  │ │  Service │
│ (Letta SDK) │ │(Letta SDK│ │(NextAuth)│
└────────┬────┘ └────┬─────┘ └────┬─────┘
         │           │            │
         └───────────┼────────────┘
                     │
        ┌────────────▼────────────┐
        │  Letta Orchestrator     │
        │  - Agent pool manager   │
        │  - Context bridge       │
        │  - Tool injection       │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   Letta Server Pool     │
        │   (Scaled instances)    │
        └────────────┬────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
┌────────▼────┐ ┌───▼────┐ ┌────▼─────┐
│ PostgreSQL  │ │ Redis  │ │  S3/R2   │
│ + pgvector  │ │(Cache) │ │ (Assets) │
└─────────────┘ └────────┘ └──────────┘
```

---

## 🔧 Component Migration Plan

### 1. **Canvas UI Migration** (Week 1-2)

**Current State:**
- `letta-code/src/canvas/` - React app served on port 3030
- Components: WorldSpace, ImmersiveStoryReader, FloatingInput, AgentSuggestions
- Styling: Custom CSS with "immersive and magical" design
- WebSocket for live updates

**Migration Strategy:**
1. **Extract Canvas as standalone Next.js app**
   ```bash
   deep-sci-fi/
   ├── apps/
   │   └── web/           # Next.js app (was letta-code/src/canvas)
   │       ├── app/
   │       │   ├── layout.tsx
   │       │   ├── page.tsx       # Canvas view
   │       │   └── api/
   │       ├── components/        # Migrated from letta-code/src/canvas/components
   │       │   ├── world/
   │       │   ├── story/
   │       │   ├── chat/          # NEW: Chat panel
   │       │   └── layout/
   │       └── styles/            # Preserve existing CSS
   ```

2. **Add Chat Panel** (integrate with existing FloatingInput)
   - Desktop: Persistent side panel (collapsible)
   - Mobile: Bottom drawer (swipe up)
   - Features:
     - Message history with agent
     - Context indicators (current world/story)
     - Quick actions (create world, start story)
     - Agent status (thinking, ready)

3. **Responsive Layout**
   ```tsx
   // Desktop (>= 1024px)
   <Layout>
     <Sidebar /> {/* Worlds list */}
     <MainCanvas /> {/* World Explorer or Story Reader */}
     <ChatPanel /> {/* Always visible */}
   </Layout>

   // Mobile (< 1024px)
   <Layout>
     <MobileNav /> {/* Bottom bar */}
     <MainCanvas /> {/* Full screen */}
     <ChatDrawer /> {/* Swipe up to open */}
   </Layout>
   ```

4. **Preserve Existing Components**
   - WorldSpace, ImmersiveStoryReader, VisualNovelReader - **NO CHANGES**
   - AgentSuggestions, FloatingInput - **EXTEND** with chat integration
   - All CSS files - **MIGRATE AS-IS**

**Deliverables:**
- [ ] Next.js app with Canvas components migrated
- [ ] Chat panel component (desktop + mobile)
- [ ] Responsive layout system
- [ ] All existing styling preserved

---

### 2. **Agent Architecture** (Week 2-3)

**Key Requirement:** Story agents MUST have access to world rules to prevent contradictions.

**Agent Types:**

```typescript
// World Agent
class WorldAgent {
  agentId: string;
  worldId: string;
  memory: {
    core: {
      foundation: Foundation;      // Rules, premise, deep focus
      elements: Element[];         // Characters, locations, tech
      constraints: Constraint[];   // Absolute rules
    };
    archival: {
      changelog: ChangelogEntry[];
      allVersions: World[];
    };
  };
  tools: [
    'world_manager',              // Save/load/diff worlds
    'assess_output_quality',      // Quality checks
    'check_logical_consistency',  // Find contradictions
    'image_generator'             // Gemini/DALL-E
  ];
}

// Story Agent
class StoryAgent {
  agentId: string;
  storyId: string;
  worldId: string;
  worldAgentId: string;          // Reference to world agent

  memory: {
    core: {
      storyContext: StoryMetadata;
      characters: Element[];       // From world
      plot: StorySegment[];
      worldRules: Rule[];          // READ-ONLY from world
    };
    archival: {
      allSegments: StorySegment[];
      branches: StoryBranch[];
    };
  };
  tools: [
    'story_manager',               // Save/load segments
    'world_query',                 // Query world agent (NEW)
    'image_generator',
    'assess_output_quality'
  ];
}
```

**Context Sharing Mechanism:**

```typescript
// Letta Orchestrator
class LettaOrchestrator {
  async getStoryAgent(storyId: string): Promise<StoryAgent> {
    const story = await db.stories.findById(storyId);
    const world = await db.worlds.findById(story.worldId);

    // Get or create world agent
    const worldAgent = await this.getWorldAgent(story.worldId);

    // Create story agent with world context injected
    const storyAgent = await lettaClient.createAgent({
      name: `story-${storyId}`,
      memory: {
        // Story-specific memory
        core: {
          storyContext: story.metadata,
          plot: story.segments,

          // CRITICAL: World rules injected as READ-ONLY
          worldRules: world.foundation.rules,
          worldElements: world.surface.visible_elements,
          worldConstraints: world.constraints
        }
      },
      tools: [
        'story_manager',
        // NEW: world_query tool for real-time world access
        this.createWorldQueryTool(worldAgent)
      ]
    });

    return storyAgent;
  }

  // Tool that allows story agent to query world agent
  createWorldQueryTool(worldAgent: WorldAgent) {
    return {
      name: 'world_query',
      description: 'Query the world agent for current rules, elements, constraints',
      async call(query: string) {
        // Story agent asks world agent directly
        return await worldAgent.query(query);
      }
    };
  }
}
```

**Benefits:**
- ✅ Story agent always has latest world rules
- ✅ Can't violate world constraints
- ✅ Can query world for clarification mid-story
- ✅ World changes propagate to all stories

**Deliverables:**
- [ ] Letta Orchestrator service
- [ ] Agent pool management
- [ ] World-Story context bridge
- [ ] `world_query` tool implementation

---

### 3. **Storage Migration** (Week 1-2)

**Current:** File-based (`.dsf/worlds/*.json`, `.dsf/stories/*/*.json`)
**Target:** PostgreSQL + S3/Cloudflare R2

**Database Schema:**

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  provider VARCHAR(50), -- 'email' or 'google'
  provider_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  preferences JSONB
);

-- Worlds
CREATE TABLE worlds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  owner_id UUID REFERENCES users(id),
  visibility VARCHAR(20) DEFAULT 'private', -- 'private', 'shared', 'public'

  -- World data (JSONB for flexibility)
  foundation JSONB NOT NULL,
  surface JSONB NOT NULL,
  constraints JSONB DEFAULT '[]',
  changelog JSONB DEFAULT '[]',

  -- Development metadata
  state VARCHAR(20) DEFAULT 'sketch',
  version INT DEFAULT 1,

  -- Agent
  world_agent_id VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- World Collaborators
CREATE TABLE world_collaborators (
  world_id UUID REFERENCES worlds(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(20) DEFAULT 'viewer', -- 'owner', 'editor', 'viewer'
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (world_id, user_id)
);

-- Stories
CREATE TABLE stories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  world_id UUID REFERENCES worlds(id) ON DELETE CASCADE,
  author_id UUID REFERENCES users(id),

  title VARCHAR(255) NOT NULL,
  metadata JSONB NOT NULL,
  world_contributions JSONB,

  -- Agent
  story_agent_id VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Story Segments
CREATE TABLE story_segments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
  parent_segment_id UUID REFERENCES story_segments(id),

  content TEXT NOT NULL,
  word_count INT,
  world_evolution JSONB,
  branches JSONB DEFAULT '[]',

  created_at TIMESTAMP DEFAULT NOW()
);

-- Assets
CREATE TABLE assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  world_id UUID REFERENCES worlds(id) ON DELETE CASCADE,
  story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES story_segments(id),

  type VARCHAR(50) NOT NULL, -- 'image', 'audio', 'video'
  storage_path VARCHAR(500) NOT NULL, -- S3 key
  description TEXT,
  generated BOOLEAN DEFAULT false,
  prompt TEXT,

  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_worlds_owner ON worlds(owner_id);
CREATE INDEX idx_stories_world ON stories(world_id);
CREATE INDEX idx_stories_author ON stories(author_id);
CREATE INDEX idx_segments_story ON story_segments(story_id);
CREATE INDEX idx_assets_world ON assets(world_id);
CREATE INDEX idx_assets_story ON assets(story_id);
```

**Tool Migration:**

```typescript
// Before: world_manager (disk-based)
// letta-code/src/tools/impl/world_manager.ts
async function saveWorld(args) {
  await writeFile(`${WORLDS_DIR}/${checkpoint}.json`, JSON.stringify(world));
}

// After: world_manager (DB-based)
// apps/api/src/services/world-manager.ts
async function saveWorld(args) {
  const { checkpoint_name, world, userId } = args;

  await db.worlds.upsert({
    where: { id: checkpoint_name },
    update: {
      foundation: world.foundation,
      surface: world.surface,
      constraints: world.constraints,
      version: world.development.version,
      updated_at: new Date()
    },
    create: {
      name: checkpoint_name,
      owner_id: userId,
      foundation: world.foundation,
      surface: world.surface,
      ...
    }
  });
}
```

**Asset Storage (S3/Cloudflare R2):**

```typescript
// Image upload flow
async function uploadAsset(file: File, worldId: string, type: 'world' | 'story') {
  const key = `${type}/${worldId}/${Date.now()}-${file.name}`;

  // Upload to S3/R2
  await s3.upload({
    Bucket: 'deep-sci-fi-assets',
    Key: key,
    Body: file,
    ContentType: file.type
  });

  // Save to DB
  await db.assets.create({
    world_id: worldId,
    type: 'image',
    storage_path: key,
    description: 'User uploaded image'
  });

  return {
    url: `https://assets.deepsci.fi/${key}`,
    key
  };
}
```

**Deliverables:**
- [ ] PostgreSQL schema migration scripts
- [ ] Updated world_manager (DB operations)
- [ ] Updated story_manager (DB operations)
- [ ] S3/R2 integration
- [ ] Asset upload/download APIs

---

### 4. **Authentication** (Week 1)

**Stack:** NextAuth.js

```typescript
// apps/web/app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import CredentialsProvider from 'next-auth/providers/credentials';
import { db } from '@/lib/db';
import bcrypt from 'bcrypt';

export const authOptions = {
  providers: [
    // Email/Password
    CredentialsProvider({
      name: 'Email',
      credentials: {
        email: { type: 'email' },
        password: { type: 'password' }
      },
      async authorize(credentials) {
        const user = await db.users.findUnique({
          where: { email: credentials.email }
        });

        if (!user || !bcrypt.compareSync(credentials.password, user.password)) {
          return null;
        }

        return { id: user.id, email: user.email, name: user.name };
      }
    }),

    // Gmail OAuth
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!
    })
  ],

  callbacks: {
    async session({ session, token }) {
      session.user.id = token.sub;
      return session;
    }
  },

  pages: {
    signIn: '/auth/signin',
    signUp: '/auth/signup'
  }
};

export default NextAuth(authOptions);
```

**UI Flow:**

```
Landing Page
    ↓
Sign In/Sign Up
    ├── Email + Password (sign up)
    └── "Continue with Google" (OAuth)
    ↓
Dashboard (Canvas)
```

**Deliverables:**
- [ ] NextAuth.js setup
- [ ] Email/password auth
- [ ] Google OAuth
- [ ] Protected routes
- [ ] Auth UI (sign in/up pages)

---

### 5. **API Layer** (Week 2-3)

**Technology:** Next.js App Router + tRPC

```typescript
// apps/web/app/api/trpc/[trpc]/route.ts
import { appRouter } from '@/server/routers';
import { createContext } from '@/server/context';

export const GET = fetchRequestHandler({
  endpoint: '/api/trpc',
  router: appRouter,
  createContext
});

// apps/web/server/routers/worlds.ts
export const worldRouter = router({
  // List user's worlds
  list: protectedProcedure
    .query(async ({ ctx }) => {
      return await db.worlds.findMany({
        where: {
          OR: [
            { owner_id: ctx.session.user.id },
            {
              collaborators: {
                some: { user_id: ctx.session.user.id }
              }
            }
          ]
        }
      });
    }),

  // Create world
  create: protectedProcedure
    .input(z.object({
      name: z.string(),
      foundation: z.object({ ... })
    }))
    .mutation(async ({ ctx, input }) => {
      // Create world in DB
      const world = await db.worlds.create({
        data: {
          name: input.name,
          owner_id: ctx.session.user.id,
          foundation: input.foundation,
          surface: { visible_elements: [] },
          constraints: []
        }
      });

      // Create world agent
      const orchestrator = new LettaOrchestrator();
      const agent = await orchestrator.createWorldAgent(world.id);

      // Update world with agent ID
      await db.worlds.update({
        where: { id: world.id },
        data: { world_agent_id: agent.id }
      });

      return world;
    }),

  // Talk to world agent
  chat: protectedProcedure
    .input(z.object({
      worldId: z.string(),
      message: z.string()
    }))
    .mutation(async ({ ctx, input }) => {
      const orchestrator = new LettaOrchestrator();
      const agent = await orchestrator.getWorldAgent(input.worldId);

      // Send message to agent
      const response = await agent.sendMessage(input.message, {
        userId: ctx.session.user.id,
        worldId: input.worldId
      });

      return response;
    })
});
```

**Deliverables:**
- [ ] tRPC router setup
- [ ] World router (CRUD + chat)
- [ ] Story router (CRUD + chat)
- [ ] Asset router (upload/download)
- [ ] Auth middleware

---

## 📅 Migration Timeline

### **Week 1: Foundation**
- [x] Database schema design
- [ ] PostgreSQL setup + migrations
- [ ] NextAuth.js authentication
- [ ] Basic Next.js app structure
- [ ] Cloudflare R2 setup for assets

### **Week 2: Storage & API**
- [ ] Migrate world_manager to DB
- [ ] Migrate story_manager to DB
- [ ] S3/R2 integration
- [ ] tRPC API setup
- [ ] Canvas components extraction
- [ ] **Asset management API (upload/download)**

### **Week 3: Immersive Features** ⭐ NEW
- [ ] Migrate VisualNovelReader component
- [ ] Migrate CharacterLayer, DialogueLine components
- [ ] Migrate MusicManager, AudioPlayer components
- [ ] Add vn_scene, ui_components, audio_tracks to DB
- [ ] Character sprite/background asset upload
- [ ] Audio asset storage and streaming

### **Week 4: Agent-Driven UI** ⭐ NEW
- [ ] Migrate DynamicRenderer component
- [ ] Migrate all primitive components (Button, Text, Image, Gallery, Card, etc.)
- [ ] Migrate experience components (Hero, ScrollSection, ProgressBar, ActionBar)
- [ ] Migrate layout components (Stack, Grid)
- [ ] ComponentSpec validation and rendering
- [ ] Agent UI interaction callbacks

### **Week 5: Agent System**
- [ ] Letta Orchestrator service
- [ ] Agent pool management
- [ ] World-Story context bridge
- [ ] world_query tool
- [ ] **create_vn_scene tool** ⭐ NEW
- [ ] **create_ui_component tool** ⭐ NEW
- [ ] **play_audio tool** ⭐ NEW

### **Week 6: UI Integration**
- [ ] Canvas components in Next.js
- [ ] Chat panel component (adaptive modes) ⭐ UPDATED
- [ ] Responsive layouts (desktop + mobile)
- [ ] Preserve all styling (neon/cyberpunk aesthetic)
- [ ] **Immersive mode chat behavior** ⭐ NEW

### **Week 7: Full Integration**
- [ ] Connect UI to tRPC API
- [ ] Agent chat in Canvas
- [ ] Real-time updates (WebSocket)
- [ ] Asset upload/display/playback
- [ ] VN scene rendering
- [ ] Agent-created UI rendering
- [ ] Audio playback integration

### **Week 8: Polish & Testing**
- [ ] Mobile responsive testing (all modes)
- [ ] E2E tests (Canvas, VN, agent UI)
- [ ] Performance optimization (image/audio loading)
- [ ] Bug fixes
- [ ] Asset CDN optimization

### **Week 9: Deployment**
- [ ] Vercel deployment (frontend)
- [ ] Railway/Render (backend)
- [ ] Supabase (database)
- [ ] Cloudflare R2 (assets + CDN)
- [ ] Audio streaming configuration

### **Week 10: Beta Testing**
- [ ] Internal testing (all experience modes)
- [ ] Fix critical issues
- [ ] Documentation (user guide, agent capabilities)
- [ ] Launch preparation

---

## 🚀 Deployment Stack

**Frontend:** Vercel
- Next.js app with Canvas
- Automatic HTTPS
- Edge caching

**Backend API:** Railway or Render
- Node.js service
- tRPC endpoints
- WebSocket support

**Database:** Supabase or Neon
- PostgreSQL with pgvector
- Connection pooling
- Automatic backups

**Assets:** Cloudflare R2
- S3-compatible object storage
- Free tier: 10GB
- Global CDN

**Letta Server:** Modal or Fly.io
- Dedicated VM
- Scaled based on load
- Isolated agent execution

---

## 📦 Project Structure

```
deep-sci-fi/
├── apps/
│   └── web/                  # Next.js app (Canvas)
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   ├── api/
│       │   └── auth/
│       ├── components/       # Migrated from letta-code/src/canvas
│       │   ├── world/
│       │   ├── story/
│       │   ├── chat/
│       │   └── layout/
│       ├── server/           # tRPC routers
│       └── styles/           # Preserve existing CSS
│
├── packages/
│   ├── db/                   # Prisma schema, migrations
│   ├── letta/                # Letta SDK wrapper
│   │   ├── orchestrator.ts
│   │   ├── world-agent.ts
│   │   └── story-agent.ts
│   └── types/                # Shared TypeScript types
│       └── dsf.ts            # Migrated from letta-code/src/types/dsf.ts
│
├── letta/                    # Existing Letta submodule
├── letta-code/               # Existing letta-code (CLI - KEEP)
├── letta-ui/                 # Existing Letta UI (KEEP)
│
├── docs/
│   ├── architecture.md
│   └── MIGRATION_PLAN.md     # This file
│
├── docker-compose.yml        # Local development
└── README.md
```

---

## ✅ Success Criteria

**Week 6 MVP:**
- [ ] User can sign up/log in with email or Gmail
- [ ] User can create a world
- [ ] User can chat with world agent in Canvas
- [ ] World is saved to database
- [ ] Canvas UI looks identical to current
- [ ] Responsive on laptop and mobile
- [ ] **Visual Novel mode renders correctly** ⭐ NEW
- [ ] **Character sprites display** ⭐ NEW
- [ ] **Background music plays** ⭐ NEW

**Week 10 Beta:**
- [ ] Full world/story management
- [ ] Image generation working (worlds + character sprites)
- [ ] Real-time updates
- [ ] Asset upload/display (images + audio)
- [ ] **Full visual novel creation by agent** ⭐ NEW
- [ ] **Agent-driven UI components working** ⭐ NEW
- [ ] **Immersive experiences (VN, Hero sections, etc.)** ⭐ NEW
- [ ] **Adaptive chat (hides in immersive mode)** ⭐ NEW
- [ ] Production deployment
- [ ] 20+ beta users testing

---

## 🎨 Design Principles

1. **Migration, not rebuild** - Preserve existing code wherever possible
2. **Immersive & magical** - Maintain current design aesthetic
3. **Mobile-first** - Responsive from day one
4. **Agent-centric** - Chat is primary interaction
5. **World integrity** - Story agents can't violate world rules

---

## 📝 Open Questions

1. **Agent pricing:** Claude API costs for multi-user (Anthropic API key per user vs shared?)
2. **Rate limiting:** How many agent messages per user per day?
3. **World size limits:** Max elements, rules, constraints per world?
4. **Collaboration:** Read-only sharing first, or full co-editing?
5. **Image generation:** Gemini preferred (free tier?), fallback to DALL-E?

---

## 📚 References

- [Current Architecture](./architecture.md)
- [Agent Context Sharing](./AGENT_CONTEXT_SHARING.md) - World ↔ Story agent communication
- [Chat UI Integration](./CHAT_UI_INTEGRATION.md) - Chat panel design
- **[Immersive Experiences](./IMMERSIVE_EXPERIENCES.md)** ⭐ NEW - Visual novel, agent UI, audio
- [Canvas UI Code](../letta-code/src/canvas/)
- [Visual Novel Components](../letta-code/src/canvas/components/story/)
- [Agent-Driven UI Components](../letta-code/src/canvas/components/)
- [World Manager Tool](../letta-code/src/tools/impl/world_manager.ts)
- [Story Manager Tool](../letta-code/src/tools/impl/story_manager.ts)
- [Letta SDK Docs](https://github.com/letta-ai/letta)

---

**Next Steps:**
1. Review this plan
2. Set up development environment
3. Start Week 1 tasks
4. Daily standups to track progress

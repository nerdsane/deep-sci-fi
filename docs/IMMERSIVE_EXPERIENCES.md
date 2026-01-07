# Immersive Experiences: Visual Novel & Agent-Driven UI

**Deep Sci-Fi is not just a world-building tool - it's a dynamic storytelling platform where agents create immersive, RPG-like experiences.**

**Key Features:**
- 📖 Visual Novel mode (character sprites, backgrounds, dialogue)
- 🎨 Agent-driven UI (custom components, layouts)
- 🎵 Audio system (background music, sound effects)
- 🎭 Character emotions and animations
- 🎬 Immersive scrolling experiences (Hero sections, parallax)
- 🌳 Branching narratives with choices

---

## 🎮 Experience Types

### 1. **Visual Novel Mode**

**What it is:** Traditional visual novel presentation with character sprites, backgrounds, and dialogue boxes.

**Components:**
- `VisualNovelReader` - Main VN renderer
- `CharacterLayer` - Character sprite positioning and animations
- `DialogueLine` - Dialogue parsing and formatting

**Features:**
```typescript
interface VNSceneData {
  id: string;
  background?: string;         // Scene background image URL
  music?: string;              // Background music URL
  characters: CharacterSprite[]; // Character sprites with positions
  lines: DialogueLineData[];   // Dialogue lines
}

interface CharacterSprite {
  characterId: string;
  imageUrl: string;
  position: 'left' | 'center' | 'right';
  emotion?: string;            // 'happy', 'sad', 'angry', etc.
  scale?: number;              // 1.0 = normal size
  offsetY?: number;            // Vertical offset in pixels
  flipped?: boolean;           // Mirror sprite horizontally
}

interface DialogueLineData {
  speaker?: string;            // Character name
  text: string;                // Dialogue text
  emotion?: string;            // Emotion tag
  isNarration?: boolean;       // True for narration
}
```

**Agent Usage:**
```typescript
// Agent creates a VN scene via tool
await story_manager({
  operation: 'save_segment',
  story_id: storyId,
  segment: {
    content: "MARCUS: \"We need to move quickly.\"",
    vnScene: {
      id: 'seg_001_scene',
      background: '/assets/city_alley_night.jpg',
      music: '/assets/music/tension.mp3',
      characters: [
        {
          characterId: 'marcus_kane',
          imageUrl: '/assets/characters/marcus_neutral.png',
          position: 'left',
          emotion: 'determined'
        },
        {
          characterId: 'elena_voss',
          imageUrl: '/assets/characters/elena_worried.png',
          position: 'right',
          emotion: 'worried'
        }
      ],
      lines: [
        { speaker: 'MARCUS', text: 'We need to move quickly.', emotion: 'determined' },
        { speaker: 'ELENA', text: 'But what about the others?', emotion: 'worried' },
        { text: 'The sound of sirens grew louder in the distance.', isNarration: true }
      ]
    }
  }
});
```

**Visual Output:**
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│         [City alley at night background]            │
│                                                      │
│  [Marcus sprite]                  [Elena sprite]    │
│   (determined)                      (worried)       │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │ 💬 MARCUS (determined)                      │    │
│  │ "We need to move quickly."                  │    │
│  │                                      ▼      │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  🎵 tension.mp3 playing                             │
└──────────────────────────────────────────────────────┘

Click or press Space to advance →
```

**Key Features:**
- Typewriter text effect (adjustable speed)
- Auto-advance option
- Branching choices at scene end
- Character speaking glow effect
- Pause menu (Esc key)
- Skip to end of line (Space/Enter)
- Progress indicator

---

### 2. **Agent-Driven UI Components**

**What it is:** Agents can create custom UI components dynamically via `ComponentSpec` JSON.

**Available Components:**

```typescript
// Primitives
- Button: Clickable buttons with variants
- Text: Formatted text with sizes/colors
- Image: Images with captions and lightbox
- Gallery: Image galleries (grid/masonry)
- Card: Content cards with images
- Timeline: Event timelines (horizontal/vertical)
- Callout: Info boxes (info/warning/success/danger)
- Stats: Stat displays (key-value pairs)
- Badge: Small labels/tags
- Divider: Section dividers

// Layout
- Stack: Flex layouts (row/column)
- Grid: CSS Grid layouts

// Experience
- Hero: Full-screen hero sections
- ScrollSection: Scroll-triggered animations
- ProgressBar: Reading progress indicators
- ActionBar: Floating action buttons

// Advanced
- Dialog: Modal dialogs
- RawJsx: Custom JSX (advanced)
```

**Example: Agent Creates a Character Profile Card**

```typescript
// Agent sends this ComponentSpec
{
  type: 'Card',
  id: 'marcus_profile',
  props: {
    title: 'Marcus Kane',
    subtitle: 'Resistance Leader',
    image: '/assets/characters/marcus_profile.png',
    variant: 'elevated',
    accent: 'cyan'
  },
  children: [
    {
      type: 'Stack',
      props: { direction: 'column', spacing: 'medium' },
      children: [
        {
          type: 'Text',
          props: {
            content: 'Former military strategist turned resistance leader...',
            variant: 'body'
          }
        },
        {
          type: 'Stats',
          props: {
            items: [
              { label: 'Faction', value: 'Resistance' },
              { label: 'Skills', value: 'Strategy, Combat' },
              { label: 'Status', value: 'Active' }
            ],
            variant: 'compact'
          }
        },
        {
          type: 'Button',
          props: {
            label: 'View Full History',
            variant: 'primary',
            onClick: 'show_character_timeline'
          }
        }
      ]
    }
  ]
}
```

**Rendered Output:**
```
┌─────────────────────────────────┐
│ ╔═══════════════════════════╗  │
│ ║  [Marcus Kane Portrait]   ║  │
│ ╚═══════════════════════════╝  │
│                                 │
│  Marcus Kane                    │
│  Resistance Leader              │
│                                 │
│  Former military strategist     │
│  turned resistance leader...    │
│                                 │
│  • Faction: Resistance          │
│  • Skills: Strategy, Combat     │
│  • Status: Active               │
│                                 │
│  ┌───────────────────────────┐ │
│  │  View Full History        │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
```

**Agent Interaction Flow:**
1. Agent creates ComponentSpec JSON
2. Sends via Agent Bus with `canvas_ui` message type
3. DynamicRenderer renders component
4. User clicks button → `onInteraction` callback
5. Message sent back to agent via Agent Bus
6. Agent responds to interaction

---

### 3. **Audio System**

**Components:**
- `MusicManager` - Background music control
- `AudioPlayer` - Sound effects and voice

**Features:**
```typescript
// Background Music
interface MusicManagerProps {
  currentTrack?: string;       // URL to audio file
  volume?: number;             // 0-1
  loop?: boolean;              // Loop track
  fadeInDuration?: number;     // Fade in time (ms)
  fadeOutDuration?: number;    // Fade out time (ms)
}

// Sound Effects
interface AudioPlayerProps {
  src: string;                 // URL to audio file
  volume?: number;
  autoplay?: boolean;
  loop?: boolean;
}
```

**Agent Usage:**
```typescript
// Start background music for a scene
{
  type: 'canvas_ui',
  target: 'music_manager',
  payload: {
    action: 'play',
    track: '/assets/music/exploration_theme.mp3',
    volume: 0.6,
    loop: true,
    fadeInDuration: 2000
  }
}

// Play sound effect
{
  type: 'canvas_ui',
  target: 'audio_player',
  payload: {
    action: 'play',
    src: '/assets/sfx/door_open.mp3',
    volume: 0.8
  }
}
```

---

## 🎨 Agent Creation Workflow

### Example: Agent Creates Immersive Story Scene

```
User: "Continue the story with Marcus entering the underground hideout"

Agent thinking:
1. This is a key moment - should be immersive
2. Create visual novel scene with:
   - Background: underground hideout
   - Characters: Marcus (entering), Elena (waiting)
   - Music: ambient underground theme
   - Dialogue: Their conversation
3. Add UI enhancements:
   - Hero section for dramatic entry
   - Character profile cards for new NPCs

Agent actions:

1. Generate background image:
   → image_generator("underground resistance hideout, dim lighting,
                      cyberpunk, neon signs, industrial")
   → Returns: /assets/worlds/dystopian-city/hideout_bg.png

2. Generate character sprite (if doesn't exist):
   → image_generator("Marcus Kane full body sprite, resistance outfit,
                      neutral expression, transparent background")
   → Returns: /assets/characters/marcus_neutral.png

3. Create VN scene:
   → story_manager({
       operation: 'save_segment',
       segment: {
         content: "...",
         vnScene: {
           background: '/assets/worlds/dystopian-city/hideout_bg.png',
           music: '/assets/music/underground_ambient.mp3',
           characters: [...],
           lines: [...]
         }
       }
     })

4. Add UI enhancement (Hero section):
   → Broadcast canvas_ui message with Hero component spec

5. Save audio references to assets table
```

---

## 💾 Database Schema Updates

### Stories Table (Updated)

```sql
-- Add VN and component data
ALTER TABLE story_segments ADD COLUMN vn_scene JSONB;
ALTER TABLE story_segments ADD COLUMN ui_components JSONB;
ALTER TABLE story_segments ADD COLUMN audio_tracks JSONB;

-- Example vn_scene data:
{
  "id": "seg_001_scene",
  "background": "/assets/worlds/dystopian-city/hideout_bg.png",
  "music": "/assets/music/underground_ambient.mp3",
  "characters": [
    {
      "characterId": "marcus_kane",
      "imageUrl": "/assets/characters/marcus_neutral.png",
      "position": "left",
      "emotion": "determined"
    }
  ],
  "lines": [
    { "speaker": "MARCUS", "text": "Finally, we're safe.", "emotion": "relieved" }
  ]
}

-- Example ui_components data:
{
  "components": [
    {
      "target": "fullscreen",
      "mode": "overlay",
      "spec": {
        "type": "Hero",
        "props": { ... }
      }
    }
  ]
}

-- Example audio_tracks data:
{
  "bgm": "/assets/music/underground_ambient.mp3",
  "sfx": [
    { "event": "door_open", "src": "/assets/sfx/door.mp3", "timestamp": 0 }
  ]
}
```

### Assets Table (Updated)

```sql
-- Add asset type categories
ALTER TABLE assets ADD COLUMN category VARCHAR(50); -- 'character', 'background', 'music', 'sfx', 'ui'
ALTER TABLE assets ADD COLUMN metadata JSONB; -- Character emotion, music duration, etc.

-- Example character sprite asset:
{
  "id": "...",
  "type": "image",
  "category": "character",
  "storage_path": "characters/marcus_neutral.png",
  "metadata": {
    "characterId": "marcus_kane",
    "emotion": "neutral",
    "hasTransparency": true,
    "dimensions": { "width": 800, "height": 1200 }
  }
}

-- Example background asset:
{
  "id": "...",
  "type": "image",
  "category": "background",
  "storage_path": "worlds/dystopian-city/hideout_bg.png",
  "metadata": {
    "scene": "underground_hideout",
    "mood": "tense",
    "dimensions": { "width": 1920, "height": 1080 }
  }
}

-- Example music asset:
{
  "id": "...",
  "type": "audio",
  "category": "music",
  "storage_path": "music/underground_ambient.mp3",
  "metadata": {
    "duration": 180, // seconds
    "loop": true,
    "mood": "ambient",
    "genre": "electronic"
  }
}
```

---

## 🎬 Chat Integration with Immersive Mode

**Challenge:** Chat panel shouldn't interfere with visual novel or fullscreen experiences.

**Solution: Adaptive Chat Behavior**

```typescript
// Chat panel behavior based on experience mode
const ChatPanelBehavior = {
  // Normal canvas view
  'canvas': {
    desktop: 'persistent-sidebar',  // Always visible on right
    mobile: 'bottom-drawer'         // Swipe up
  },

  // Visual novel mode
  'visual-novel': {
    desktop: 'minimized-floating',  // Small bubble in corner
    mobile: 'hidden'                // Completely hidden
  },

  // Fullscreen experience (Hero, etc.)
  'fullscreen': {
    desktop: 'hidden',              // Hide completely
    mobile: 'hidden'
  },

  // Reading mode (ImmersiveStoryReader)
  'reading': {
    desktop: 'minimal-sidebar',     // Thin sidebar, collapsed
    mobile: 'floating-bubble'       // Small bubble
  }
};
```

**Visual States:**

```
Normal Canvas Mode (Desktop):
┌────────┬──────────────────┬──────────┐
│ Worlds │   Canvas         │  Chat    │
│        │                  │          │
└────────┴──────────────────┴──────────┘

Visual Novel Mode (Desktop):
┌──────────────────────────────────┐
│                                  │
│      [VN Scene Fullscreen]       │
│                                  │
│  [Dialogue Box]                  │
│                                  │
│            💬 [Chat Bubble]      │ ← Minimized in corner
└──────────────────────────────────┘

Fullscreen Experience (Hero):
┌──────────────────────────────────┐
│                                  │
│      [Hero Section]              │
│                                  │
│                                  │
│                                  │
│                                  │
└──────────────────────────────────┘
No chat visible (Esc to exit)
```

**User Actions:**
- **In VN mode:** Click chat bubble → Pause VN, show chat panel
- **In fullscreen:** Press Esc → Exit fullscreen, restore chat
- **Desktop:** Cmd+K always opens chat (minimizes VN if needed)
- **Mobile:** Swipe up always works (pauses immersive mode)

---

## 🚀 Migration Additions

### Week 2-3: Immersive Features (NEW)

**Visual Novel Components:**
- [ ] Migrate VisualNovelReader component
- [ ] Migrate CharacterLayer component
- [ ] Migrate DialogueLine component
- [ ] Add VN scene data to story_segments table
- [ ] Create character sprite asset upload

**Audio System:**
- [ ] Migrate MusicManager component
- [ ] Migrate AudioPlayer component
- [ ] Add audio asset storage (S3/R2)
- [ ] Create audio playback API

**Agent-Driven UI:**
- [ ] Migrate DynamicRenderer component
- [ ] Migrate all primitive components (Button, Text, Image, etc.)
- [ ] Migrate experience components (Hero, ScrollSection, etc.)
- [ ] Add ui_components column to story_segments
- [ ] Create ComponentSpec validation

**Asset Management:**
- [ ] Extend assets table (category, metadata)
- [ ] Character sprite upload/management
- [ ] Background image upload/management
- [ ] Audio file upload/management
- [ ] Asset CDN configuration (Cloudflare R2)

### Week 4: Agent Tools (UPDATED)

**New Agent Tools:**
- [ ] `create_vn_scene` - Create visual novel scene with sprites/bg
- [ ] `update_vn_scene` - Modify existing VN scene
- [ ] `create_ui_component` - Send ComponentSpec to canvas
- [ ] `play_audio` - Control background music/sound effects
- [ ] `generate_character_sprite` - Generate character art (via image_generator)

---

## 📦 Asset Storage Structure

```
s3://deep-sci-fi-assets/
├── characters/           # Character sprites
│   ├── marcus_neutral.png
│   ├── marcus_happy.png
│   ├── marcus_angry.png
│   └── elena_worried.png
├── backgrounds/          # Scene backgrounds
│   └── worlds/
│       └── dystopian-city/
│           ├── hideout_bg.png
│           ├── corporate_zone.png
│           └── neutral_zone.png
├── music/                # Background music
│   ├── exploration_theme.mp3
│   ├── tension.mp3
│   └── victory.mp3
├── sfx/                  # Sound effects
│   ├── door_open.mp3
│   ├── footsteps.mp3
│   └── gunshot.mp3
└── ui/                   # UI images (icons, logos)
    └── ...
```

**File Size Limits:**
- Character sprites: 2MB (PNG with transparency)
- Backgrounds: 5MB (JPG/PNG, 1920x1080 recommended)
- Music: 10MB (MP3/OGG, stereo, 192kbps)
- Sound effects: 1MB (MP3/OGG, mono, 128kbps)

**CDN Configuration:**
- Cloudflare R2 with CDN
- Public access for assets (no auth required)
- Automatic image optimization (WebP conversion)
- Audio streaming support

---

## ✅ Summary

**Deep Sci-Fi's Immersive Features:**

1. **Visual Novel Mode**
   - Character sprites with positions and emotions
   - Scene backgrounds
   - Typewriter dialogue with auto-advance
   - Branching choices
   - Pause menu and controls

2. **Agent-Driven UI**
   - 20+ component types
   - Dynamic component creation
   - Interaction callbacks
   - Fullscreen experiences (Hero sections)

3. **Audio System**
   - Background music with fade in/out
   - Sound effects
   - Looping support

4. **Assets**
   - Character sprites (transparent PNG)
   - Scene backgrounds (high-res images)
   - Music tracks (MP3/OGG)
   - Sound effects

**Migration Impact:**
- Database schema: +3 columns (vn_scene, ui_components, audio_tracks)
- Asset storage: +4 categories (character, background, music, sfx)
- Agent tools: +5 new tools
- Components: +15 components to migrate
- Timeline: +1 week (immersive features week)

**Result:** A fully immersive storytelling platform where agents can create RPG-like experiences dynamically, not just text stories.

---

**Next:** Update [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) to include immersive features timeline.

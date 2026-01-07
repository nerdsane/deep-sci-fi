# Multimedia Integration: Where Can Agent Incorporate Images?

## TL;DR: Progression from Simple to Flexible

```
Phase 1 (Now):     Images attached to segments/worlds
                   ↓
Phase 2 (Simple):  Images inline via markdown
                   ↓
Phase 3 (Dynamic): Agent creates custom UI layouts with positioned images
```

---

## Current Data Model (What's Already Supported)

### 1. Story Segments Can Have Multiple Assets

```typescript
interface StorySegment {
  id: string;
  content: string;           // Narrative text
  word_count: number;

  assets?: StoryAsset[];     // ← Images, audio, video

  world_evolution: { /* ... */ };
  branches?: StoryBranch[];
}

interface StoryAsset {
  id: string;
  type: "image" | "audio" | "video" | "document";
  path: string;              // "the_neural_canvas/img_1735635000.png"
  description?: string;      // "Neural interface headset"
  generated?: boolean;       // true if AI-generated
  prompt?: string;           // "Watercolor neural headset..."
}
```

**Currently:** Agent can attach multiple images to each segment.

### 2. Worlds Can Have Cover Images

```typescript
interface World {
  development: { /* ... */ };
  surface: { /* ... */ };
  foundation: { /* ... */ };

  asset?: StoryAsset;        // ← World cover image
}
```

**Currently:** Agent can give each world a hero image.

---

## Phase 1: Current State (With Shared Agent Fix)

### What Agent Can Do NOW

**1. Generate images:**
```typescript
image_generator({
  prompt: "Watercolor style: Neural interface headset, soft blues and purples",
  provider: "google",
  save_as_asset: true,
  story_id: "the_neural_canvas"
})

// Returns: { asset_id: "img_1735635000", path: "the_neural_canvas/img_1735635000.png" }
```

**2. Attach images to segments:**
```typescript
story_manager({
  operation: "save_segment",
  story_id: "the_neural_canvas",
  segment: {
    content: "She put on the headset. The world shifted, colors bleeding into sound...",
    word_count: 520,
    parent_segment: "seg_002",

    assets: [                                    // ← Images attached here
      {
        id: "img_1735635000",
        type: "image",
        path: "the_neural_canvas/img_1735635000.png",
        description: "Neural interface headset",
        generated: true,
        prompt: "Watercolor neural headset..."
      }
    ],

    world_evolution: { /* ... */ }
  }
})
```

**3. Add world cover images:**
```typescript
world_manager({
  operation: "save",
  checkpoint_name: "neural_art_2035",
  world: {
    // ... world data ...
    asset: {                                     // ← World cover
      id: "world_cover_123",
      type: "image",
      path: "worlds/neural_art_2035/cover.png",
      description: "Neural Art Gallery 2035"
    }
  }
})
```

### Where Images Appear (Current)

**Web UI:**
```tsx
// Story segment view (app.tsx lines 527-544)
{segment.assets && segment.assets.length > 0 && (
  <div className="segment-assets">
    {segment.assets.map((asset) => (
      <div key={asset.id} className="asset-item">
        {asset.type === "image" && (
          <img
            src={`/assets/${asset.path}`}
            alt={asset.description || "Story asset"}
            className="asset-image"
          />
        )}
        {asset.description && (
          <p className="asset-description">{asset.description}</p>
        )}
      </div>
    ))}
  </div>
)}
```

**Images appear at TOP of segment** (before text content).

**CLI:**
```
Segment 3:
[Image: Neural interface headset]

She put on the headset. The world shifted, colors bleeding into sound...
```

Shows `[Image: description]` markers.

### Limitations

❌ **No inline placement** - images always at top
❌ **No positioning** - can't put image left/right/center
❌ **No effects** - no parallax, fade, etc.
❌ **Fixed layout** - web UI has one way to display

### But It Works!

✅ Agent can generate images
✅ Agent can attach to segments
✅ Web UI displays them
✅ CLI shows markers

**This is functional, just not flexible yet.**

---

## Phase 2: Inline Markdown Images (Simple Enhancement)

### What Changes

**Agent writes markdown with image markers:**
```typescript
story_manager({
  operation: "save_segment",
  segment: {
    content: `She approached the gallery entrance.

![](img_neural_gallery)

The building itself was a work of art, its façade rippling with neural patterns...

Inside, she found the headset waiting. ![](img_headset) It gleamed under the soft lights...`,

    assets: [
      { id: "img_neural_gallery", type: "image", path: "..." },
      { id: "img_headset", type: "image", path: "..." }
    ]
  }
})
```

**Web UI renders markdown:**
```tsx
// Segment display with markdown renderer
import ReactMarkdown from 'react-markdown';

<ReactMarkdown
  content={segment.content}
  components={{
    img: ({ node, ...props }) => {
      // Resolve asset ID to actual path
      const assetId = props.src;  // "img_neural_gallery"
      const asset = segment.assets?.find(a => a.id === assetId);

      if (!asset) return null;

      return (
        <img
          src={`/assets/${asset.path}`}
          alt={asset.description || ''}
          className="inline-image"
        />
      );
    }
  }}
/>
```

**CLI shows inline markers:**
```
She approached the gallery entrance.

[Image: Neural Art Gallery exterior]

The building itself was a work of art, its façade rippling with neural patterns...

Inside, she found the headset waiting. [Image: Neural headset] It gleamed under the soft lights...
```

### Where Images Can Appear

✅ **Anywhere in narrative flow** - agent decides placement
✅ **Multiple images per segment** - as many as needed
✅ **Inline with text** - images between paragraphs or sentences

### Still Simple

- No complex positioning (left/right/float)
- No effects (parallax, etc.)
- Just markdown `![](id)` → `<img>` rendering

**Effort: ~2 hours** (add markdown renderer, asset resolution)

---

## Phase 3: Dynamic UI (Future - Full Flexibility)

### Agent Creates Custom Layouts

**New tool: `ui_composer`**

Agent can create **custom UI experiences** for special moments:

```typescript
ui_composer({
  operation: "create",
  experience: {
    id: "neural_gallery_reveal",
    type: "story_moment",

    layout: {
      type: "grid",
      columns: 2,
      regions: [
        { id: "left", span: 1 },
        { id: "right", span: 1 }
      ]
    },

    components: [
      // Left side: Large hero image
      {
        type: "image",
        props: {
          asset_id: "img_neural_gallery",
          size: "large",
          effects: ["parallax"],
          caption: "The Neural Art Gallery"
        },
        position: { region: "left", order: 1 }
      },

      // Right side: Narrative text
      {
        type: "narrative",
        props: {
          content: "She approached the gallery entrance...",
          styling: "atmospheric"
        },
        position: { region: "right", order: 1 }
      },

      // Right side: Image gallery
      {
        type: "gallery",
        props: {
          asset_ids: ["img_exhibit_1", "img_exhibit_2", "img_exhibit_3"],
          layout: "carousel",
          autoplay: false
        },
        position: { region: "right", order: 2 }
      },

      // Bottom: Interactive choice
      {
        type: "choice_buttons",
        props: {
          prompt: "What does she do?",
          choices: [
            { label: "Enter the gallery", value: "enter" },
            { label: "Observe from outside", value: "observe" }
          ]
        },
        position: { region: "right", order: 3 }
      }
    ]
  }
})
```

### Web UI Renders Dynamic Experience

```tsx
// Experience renderer
function ExperienceRenderer({ experience }: { experience: Experience }) {
  const layout = getLayoutComponent(experience.layout.type);  // Grid, Split, Tabs, etc.

  return (
    <layout.Component layout={experience.layout}>
      {experience.components.map(component => {
        const Component = getComponentByType(component.type);
        return (
          <Component
            key={component.id}
            {...component.props}
            position={component.position}
            styling={component.styling}
          />
        );
      })}
    </layout.Component>
  );
}
```

### Where Images Can Appear (Full Flexibility)

✅ **Hero images** - full-width, parallax backgrounds
✅ **Side-by-side** - image + text in columns
✅ **Galleries** - carousels, grids, lightboxes
✅ **Floating** - images that scroll with parallax
✅ **Interactive** - click to zoom, pan, reveal
✅ **Character cards** - portrait + bio layout
✅ **Timelines** - events with images
✅ **Maps** - annotated world geography
✅ **Comparisons** - before/after, split views

### Agent Decides When to Use

**Normal segments:** Just markdown images (Phase 2)
**Special moments:** Create dynamic experience (Phase 3)

```typescript
// Agent decides: "This is a key character reveal, make it special"
ui_composer({
  type: "character_focus",
  components: [
    { type: "image", props: { asset_id: "nia_portrait" } },
    { type: "narrative", props: { content: "..." } },
    { type: "timeline", props: { events: [...] } }
  ]
})

// Agent decides: "This is just normal narrative, use markdown"
story_manager({
  operation: "save_segment",
  segment: {
    content: "She walked through the city. ![](img_city) The buildings towered..."
  }
})
```

**Agent has both simple and complex tools, uses appropriately.**

---

## Visual Comparison

### Phase 1: Current (Segment-Level Assets)

```
┌─────────────────────────────────────────┐
│ Segment 3                               │
│                                         │
│ ┌─────────────────────────────────┐   │
│ │                                 │   │
│ │  [Neural Headset Image]         │   │
│ │                                 │   │
│ └─────────────────────────────────┘   │
│                                         │
│ She put on the headset. The world       │
│ shifted, colors bleeding into sound.    │
│ Every sensation became visible...       │
└─────────────────────────────────────────┘
```

**Images at top, text below.**

---

### Phase 2: Inline Markdown

```
┌─────────────────────────────────────────┐
│ Segment 3                               │
│                                         │
│ She approached the gallery entrance.    │
│                                         │
│ ┌─────────────────────────────────┐   │
│ │  [Gallery Exterior]             │   │
│ └─────────────────────────────────┘   │
│                                         │
│ The building itself was a work of art.  │
│ Inside, she found the headset.          │
│                                         │
│  ┌───────────┐                          │
│  │ [Headset] │ It gleamed under the     │
│  └───────────┘ soft lights...           │
└─────────────────────────────────────────┘
```

**Images anywhere agent chooses, inline with text.**

---

### Phase 3: Dynamic UI

```
┌──────────────────────────────────────────────────────────┐
│ Character Reveal: Nia Chen                               │
├────────────────────┬─────────────────────────────────────┤
│                    │  Nia Chen                           │
│                    │  Neural Artist                      │
│  ┌──────────────┐ │                                     │
│  │              │ │  She never wanted to be an artist.  │
│  │  [Portrait]  │ │  She wanted to be a surgeon...      │
│  │              │ │                                     │
│  │              │ │  ┌─────────────────────────────┐   │
│  └──────────────┘ │  │ Timeline                    │   │
│                    │  │ 2025: Neural accident       │   │
│  "Every sensation  │  │ 2027: First breakthrough   │   │
│   became visible"  │  │ 2035: Present day          │   │
│                    │  └─────────────────────────────┘   │
│                    │                                     │
│                    │  [The accident] [Her art] [Continue]│
└────────────────────┴─────────────────────────────────────┘
```

**Agent-composed layout: image, text, timeline, choices all positioned.**

---

## Where Agent Can Put Images: Summary Table

| Location | Phase 1 (Current) | Phase 2 (Markdown) | Phase 3 (Dynamic) |
|----------|-------------------|-------------------|-------------------|
| **Segment assets** | ✅ Top of segment | ✅ Top of segment | ✅ Top of segment |
| **Inline in text** | ❌ | ✅ Via `![](id)` | ✅ Via markdown or components |
| **World covers** | ✅ Hero image | ✅ Hero image | ✅ Hero image + effects |
| **Side-by-side** | ❌ | ❌ | ✅ Grid/split layouts |
| **Galleries** | ❌ | ❌ | ✅ Carousel component |
| **Character cards** | ❌ | ❌ | ✅ Custom layout |
| **Timelines** | ❌ | ❌ | ✅ Timeline component with images |
| **Maps** | ❌ | ❌ | ✅ Annotated map component |
| **Floating/Parallax** | ❌ | ❌ | ✅ Effects in layouts |
| **Interactive** | ❌ | ❌ | ✅ Zoom, pan, reveal |

---

## Example: Agent Creates Multimedia Story

### Segment 1: Normal narrative (Phase 2)

```typescript
story_manager({
  segment: {
    content: `She walked through the city. ![](img_city_street)

The rain-slicked streets reflected the neon signs, creating a mirror world beneath her feet.

At the corner, she saw the gallery. ![](img_gallery_exterior) Its entrance pulsed with soft light.`,

    assets: [
      { id: "img_city_street", type: "image", path: "..." },
      { id: "img_gallery_exterior", type: "image", path: "..." }
    ]
  }
})
```

**Web:** Images inline in narrative flow
**CLI:** `[Image: City street]` markers

---

### Segment 2: Special moment (Phase 3)

Agent detects: "This is a key reveal - make it immersive"

```typescript
ui_composer({
  experience: {
    type: "story_moment",
    layout: { type: "fullscreen" },
    components: [
      {
        type: "image",
        props: {
          asset_id: "img_gallery_interior",
          size: "fullscreen",
          effects: ["parallax"],
          overlay_text: "The Neural Art Gallery"
        }
      },
      {
        type: "narrative",
        props: {
          content: "She stepped inside. The world exploded into sensation...",
          styling: {
            position: "bottom",
            background: "gradient-fade"
          }
        }
      }
    ]
  }
})
```

**Web:** Full-screen image with parallax, text overlaid
**CLI:** Simplified text version

---

### Segment 3: Character focus (Phase 3)

```typescript
ui_composer({
  experience: {
    type: "character_focus",
    layout: { type: "split" },
    components: [
      { type: "image", props: { asset_id: "nia_portrait" }, position: { region: "left" } },
      { type: "narrative", props: { content: "..." }, position: { region: "right" } },
      { type: "timeline", props: { events: [...] }, position: { region: "right" } }
    ]
  }
})
```

**Web:** Split layout with portrait, bio, timeline
**CLI:** Text with `[Portrait: Nia Chen]` marker

---

## Implementation Effort

| Phase | Effort | Benefit |
|-------|--------|---------|
| **Phase 1** (Current) | 0 hours (already works!) | Basic image support |
| **Phase 2** (Markdown) | ~2 hours | Inline images anywhere |
| **Phase 3** (Dynamic UI) | ~20-30 hours | Full flexibility |

**Recommended:** Start with Phase 1 (fix shared agent), then Phase 2 (markdown), then consider Phase 3 based on actual needs.

---

## Key Insight

**Agent flexibility depends on available tools:**

- **Phase 1:** Agent has `image_generator` + `story_manager` → Can attach images to segments
- **Phase 2:** Agent writes markdown `![](id)` → Can place images inline
- **Phase 3:** Agent has `ui_composer` → Can create custom layouts

**Each phase builds on the previous.** No need to jump straight to Phase 3.

---

## Recommendation

### Start Simple (Phase 1 + 2)

1. **Implement shared agent** (~6 hours) - Web can invoke agent
2. **Add markdown renderer** (~2 hours) - Inline images work
3. **Update agent prompt:** "You can place images inline using ![](asset_id)"

**Total: ~8 hours**

**Result:** Agent can generate images, place them anywhere in narrative flow, user sees them in both CLI and web.

### Later: Dynamic UI (Phase 3)

Once basic multimedia works and you've used it for a while:

4. **Design component library** - What layouts are actually useful?
5. **Implement `ui_composer` tool** - Agent can create experiences
6. **Build web renderer** - Interprets experience JSON
7. **Update agent prompt** - When to use dynamic vs. markdown

**Total: ~20-30 hours**

**Result:** Agent can create custom UI moments for special narrative beats.

---

## Answer to Your Question

**"Where will agent be able to incorporate images?"**

**Phase 1 (Current):**
- Top of story segments
- World cover images

**Phase 2 (Simple + 8 hours):**
- Anywhere inline in narrative text
- Agent decides placement via markdown

**Phase 3 (Dynamic + 30 hours):**
- Custom layouts (split, grid, fullscreen)
- Galleries and carousels
- Character cards with portraits
- Timelines with images
- Maps and diagrams
- Interactive experiences

**The architecture supports all three phases.** Start simple, add flexibility as needed.

**Dynamic UI is definitely feasible** - just not the first thing to build. Get shared agent + markdown working first, then you'll know what dynamic layouts would actually be useful based on real usage.

# Agent B Handoff: Phase 3 - World Space Evolution

**Repository:** https://github.com/rita-aga/deep-sci-fi
**Branch:** main
**Duration:** 2-3 weeks
**Status File:** `.progress/016_phase3_world_space_status.md`

---

## Your Mission

Transform the world detail view from "flat sections" into an **explorable 3D space** with interactive maps, tech artifacts, character reveals, and story portals - making users feel like they're **IN the world, not reading ABOUT it**.

**Key Constraint:** Phase 0 (Standards Migration) is running **IN PARALLEL** by Agent A. They'll integrate your components into their catalog as you build them.

---

## Context: The Vision

### Current State (What Exists)
**Observatory (3D landing page):**
- ✅ 3D world orbs in space
- ✅ Zoom-to-enter warp animation
- ✅ Agent presence glyph
- ✅ Floating suggestions

**World Detail View (Flat, needs work):**
- ❌ Sections: Rules, Locations, Technologies, Timeline
- ❌ List-based UI (not immersive)
- ❌ No spatial sense
- ❌ No interactivity

### Target State (Your Goal)

**World Space (Immersive exploration):**
- ✅ Interactive world map (locations as visual points)
- ✅ 3D tech artifacts (rotatable objects)
- ✅ Character silhouettes → dramatic reveals
- ✅ Story portals (visual gateways to narratives)
- ✅ Per-world ambient audio
- ✅ Dynamic shaders (mood-reactive)

**Design Philosophy:**
- **Spatial, not flat** - Locations are places, not list items
- **Interactive, not static** - Hover reveals, click explores
- **Mysterious, not obvious** - Characters hidden until revealed in stories
- **Cinematic, not clinical** - Every interaction feels weighted

### Research Background
Read `.progress/013_20260110_immersive-ux-ultraplan.md` sections:
- "Layer 2: The World Space"
- "Phase 3: World Space Evolution"

---

## Your Goals

### Week 1: Interactive World Map
1. ✅ Build `InteractiveWorldMap` component
2. ✅ Location visualization (points on illustrated map)
3. ✅ Hover previews (show location description)
4. ✅ Connection paths (lines/roads between locations)
5. ✅ Define TypeScript prop interfaces in `types.ts`

**End of Week 1 Checkpoint:**
- Commit `types.ts` with **all** Phase 3 prop interfaces
- Agent A will use these to create Zod schemas

### Week 2: Enhanced Elements
1. ✅ Build `TechArtifact` component (3D rotatable objects)
2. ✅ Build `CharacterReveal` component (silhouettes → full reveal)
3. ✅ Build `StoryPortal` component (visual gateway to stories)
4. ✅ Test all components with current Agent Bus

### Week 3: Atmospheric Integration
1. ✅ Per-world ambient audio system
2. ✅ Dynamic shader moods (shader colors change per world)
3. ✅ Particle effects per location type
4. ✅ Polish and edge cases

---

## Technical Implementation

### Component 1: InteractiveWorldMap

**File:** `apps/web/components/canvas/world/InteractiveWorldMap.tsx`

```tsx
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';

export interface Location {
  id: string;
  name: string;
  description: string;
  position: { x: number; y: number };  // Position on map (0-1 range)
  type: 'city' | 'landmark' | 'wilderness' | 'facility';
  imageUrl?: string;
}

export interface Connection {
  from: string;  // Location ID
  to: string;    // Location ID
  type: 'road' | 'path' | 'route';
}

export interface WorldMapProps {
  worldId: string;
  locations: Location[];
  connections?: Connection[];
  backgroundImageUrl?: string;  // Illustrated map background
  selectedLocation?: string;
  onLocationClick?: (locationId: string) => void;
  onLocationHover?: (locationId: string | null) => void;
}

export function InteractiveWorldMap({
  worldId,
  locations,
  connections = [],
  backgroundImageUrl,
  selectedLocation,
  onLocationClick,
  onLocationHover,
}: WorldMapProps) {
  const [hoveredLocation, setHoveredLocation] = useState<string | null>(null);

  const handleLocationClick = (locationId: string) => {
    onLocationClick?.(locationId);
  };

  const handleLocationHover = (locationId: string | null) => {
    setHoveredLocation(locationId);
    onLocationHover?.(locationId);
  };

  const location = hoveredLocation ? locations.find(l => l.id === hoveredLocation) : null;

  return (
    <div className="relative w-full h-full">
      {/* Map background */}
      {backgroundImageUrl && (
        <div
          className="absolute inset-0 bg-cover bg-center opacity-30"
          style={{ backgroundImage: `url(${backgroundImageUrl})` }}
        />
      )}

      {/* SVG for connections */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {connections.map((conn, i) => {
          const from = locations.find(l => l.id === conn.from);
          const to = locations.find(l => l.id === conn.to);
          if (!from || !to) return null;

          const x1 = `${from.position.x * 100}%`;
          const y1 = `${from.position.y * 100}%`;
          const x2 = `${to.position.x * 100}%`;
          const y2 = `${to.position.y * 100}%`;

          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="rgba(255, 255, 255, 0.2)"
              strokeWidth="2"
              strokeDasharray={conn.type === 'path' ? '5,5' : undefined}
            />
          );
        })}
      </svg>

      {/* Location markers */}
      {locations.map((loc) => (
        <motion.div
          key={loc.id}
          className="absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 cursor-pointer"
          style={{
            left: `${loc.position.x * 100}%`,
            top: `${loc.position.y * 100}%`,
          }}
          whileHover={{ scale: 1.5 }}
          onMouseEnter={() => handleLocationHover(loc.id)}
          onMouseLeave={() => handleLocationHover(null)}
          onClick={() => handleLocationClick(loc.id)}
        >
          <div
            className={`
              w-full h-full rounded-full border-2
              ${selectedLocation === loc.id ? 'border-cyan-400 bg-cyan-400/50' : 'border-white/50 bg-white/20'}
              ${hoveredLocation === loc.id ? 'shadow-lg shadow-cyan-400/50' : ''}
            `}
          />
        </motion.div>
      ))}

      {/* Hover preview */}
      {location && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-4 left-4 bg-black/80 p-4 rounded-lg max-w-xs"
        >
          <h3 className="text-lg font-bold text-white">{location.name}</h3>
          <p className="text-sm text-gray-300 mt-2">{location.description}</p>
          {location.imageUrl && (
            <img
              src={location.imageUrl}
              alt={location.name}
              className="mt-2 w-full h-24 object-cover rounded"
            />
          )}
        </motion.div>
      )}
    </div>
  );
}
```

---

### Component 2: TechArtifact

**File:** `apps/web/components/canvas/world/TechArtifact.tsx`

```tsx
'use client';

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import { motion } from 'framer-motion';

export interface TechArtifactProps {
  artifactId: string;
  name: string;
  description: string;
  specifications?: string;
  limitations?: string;
  model3dUrl?: string;  // Optional 3D model URL
  fallbackColor?: string;  // If no 3D model, show colored sphere
  onInspect?: () => void;
}

function RotatingModel({ url, color }: { url?: string; color: string }) {
  const meshRef = useRef<any>(null);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.01;
    }
  });

  // If 3D model provided, use it; otherwise fallback to sphere
  if (url) {
    const { scene } = useGLTF(url);
    return <primitive ref={meshRef} object={scene} scale={0.5} />;
  }

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshStandardMaterial color={color} metalness={0.8} roughness={0.2} />
    </mesh>
  );
}

export function TechArtifact({
  artifactId,
  name,
  description,
  specifications,
  limitations,
  model3dUrl,
  fallbackColor = '#00d9ff',
  onInspect,
}: TechArtifactProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-black/60 p-6 rounded-lg border border-cyan-500/30"
    >
      {/* 3D Preview */}
      <div className="w-full h-48 mb-4">
        <Canvas camera={{ position: [0, 0, 3] }}>
          <ambientLight intensity={0.5} />
          <spotLight position={[10, 10, 10]} angle={0.15} />
          <RotatingModel url={model3dUrl} color={fallbackColor} />
          <OrbitControls enableZoom={false} />
        </Canvas>
      </div>

      {/* Info */}
      <h3 className="text-xl font-bold text-white mb-2">{name}</h3>
      <p className="text-sm text-gray-300 mb-4">{description}</p>

      {specifications && (
        <div className="mb-2">
          <h4 className="text-xs font-bold text-cyan-400 uppercase">Specifications</h4>
          <p className="text-xs text-gray-400">{specifications}</p>
        </div>
      )}

      {limitations && (
        <div className="mb-4">
          <h4 className="text-xs font-bold text-orange-400 uppercase">Limitations</h4>
          <p className="text-xs text-gray-400">{limitations}</p>
        </div>
      )}

      <button
        onClick={onInspect}
        className="w-full py-2 bg-cyan-500/20 hover:bg-cyan-500/40 border border-cyan-500/50 rounded text-cyan-400 text-sm transition-colors"
      >
        Inspect Details
      </button>
    </motion.div>
  );
}
```

---

### Component 3: CharacterReveal

**File:** `apps/web/components/canvas/world/CharacterReveal.tsx`

```tsx
'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface CharacterRevealProps {
  characterId: string;
  name?: string;  // Only shown if revealed
  imageUrl?: string;  // Only shown if revealed
  bio?: string;  // Only shown if revealed
  revealed: boolean;  // Whether character has been encountered in stories
  onReveal?: () => void;  // Called when user clicks to reveal
}

export function CharacterReveal({
  characterId,
  name,
  imageUrl,
  bio,
  revealed,
  onReveal,
}: CharacterRevealProps) {
  const [isAnimating, setIsAnimating] = useState(false);

  const handleClick = () => {
    if (!revealed && onReveal) {
      setIsAnimating(true);
      setTimeout(() => {
        onReveal();
        setIsAnimating(false);
      }, 1000);
    }
  };

  return (
    <motion.div
      className="relative w-48 h-64 cursor-pointer"
      whileHover={!revealed ? { scale: 1.05 } : {}}
      onClick={handleClick}
    >
      <AnimatePresence mode="wait">
        {!revealed ? (
          // Silhouette (unrevealed)
          <motion.div
            key="silhouette"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="absolute inset-0 bg-gradient-to-b from-gray-800 to-gray-900 rounded-lg border border-gray-700"
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-gray-700/50 border-2 border-gray-600" />
                <p className="text-gray-500 text-sm">???</p>
                <p className="text-gray-600 text-xs mt-2">Encounter in stories to reveal</p>
              </div>
            </div>
          </motion.div>
        ) : (
          // Full reveal
          <motion.div
            key="revealed"
            initial={{ opacity: 0, scale: 1.2 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute inset-0 bg-gradient-to-b from-cyan-900/30 to-black rounded-lg border border-cyan-500/50 overflow-hidden"
          >
            {imageUrl && (
              <img
                src={imageUrl}
                alt={name}
                className="w-full h-40 object-cover"
              />
            )}
            <div className="p-4">
              <h3 className="text-lg font-bold text-white">{name}</h3>
              <p className="text-xs text-gray-400 mt-2 line-clamp-3">{bio}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Reveal animation overlay */}
      {isAnimating && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 1 }}
          className="absolute inset-0 bg-cyan-400/30 rounded-lg pointer-events-none"
        />
      )}
    </motion.div>
  );
}
```

---

### Component 4: StoryPortal

**File:** `apps/web/components/canvas/world/StoryPortal.tsx`

```tsx
'use client';

import { motion } from 'framer-motion';

export interface StoryPortalProps {
  storyId: string;
  title: string;
  description: string;
  coverImageUrl?: string;
  progress?: number;  // 0-1, reading progress
  branchCount?: number;  // Number of story branches
  onEnter?: () => void;
}

export function StoryPortal({
  storyId,
  title,
  description,
  coverImageUrl,
  progress = 0,
  branchCount = 1,
  onEnter,
}: StoryPortalProps) {
  return (
    <motion.div
      className="relative w-64 h-80 cursor-pointer group"
      whileHover={{ scale: 1.05 }}
      onClick={onEnter}
    >
      {/* Portal frame */}
      <div className="absolute inset-0 rounded-lg border-2 border-cyan-500/50 bg-gradient-to-b from-cyan-900/20 to-black/80 overflow-hidden">
        {/* Cover image */}
        {coverImageUrl && (
          <div className="relative w-full h-48 overflow-hidden">
            <img
              src={coverImageUrl}
              alt={title}
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
            />
            {/* Vignette overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent" />
          </div>
        )}

        {/* Story info */}
        <div className="p-4">
          <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
          <p className="text-xs text-gray-400 line-clamp-2">{description}</p>

          {/* Progress bar */}
          {progress > 0 && (
            <div className="mt-3">
              <div className="w-full h-1 bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-cyan-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">{Math.round(progress * 100)}% complete</p>
            </div>
          )}

          {/* Branch indicator */}
          {branchCount > 1 && (
            <div className="mt-2 flex items-center text-xs text-cyan-400">
              <span>⟡</span>
              <span className="ml-1">{branchCount} branches</span>
            </div>
          )}
        </div>
      </div>

      {/* Glow effect on hover */}
      <motion.div
        className="absolute inset-0 rounded-lg bg-cyan-500/0 group-hover:bg-cyan-500/10 transition-colors pointer-events-none"
      />
    </motion.div>
  );
}
```

---

### TypeScript Prop Interfaces (Week 1 End)

**File:** `apps/web/components/canvas/world/types.ts`

```typescript
// CRITICAL: Define ALL interfaces here by end of Week 1
// Agent A will use these to create Zod schemas

export interface Location {
  id: string;
  name: string;
  description: string;
  position: { x: number; y: number };
  type: 'city' | 'landmark' | 'wilderness' | 'facility';
  imageUrl?: string;
}

export interface Connection {
  from: string;
  to: string;
  type: 'road' | 'path' | 'route';
}

export interface WorldMapProps {
  worldId: string;
  locations: Location[];
  connections?: Connection[];
  backgroundImageUrl?: string;
  selectedLocation?: string;
  onLocationClick?: (locationId: string) => void;
  onLocationHover?: (locationId: string | null) => void;
}

export interface TechArtifactProps {
  artifactId: string;
  name: string;
  description: string;
  specifications?: string;
  limitations?: string;
  model3dUrl?: string;
  fallbackColor?: string;
  onInspect?: () => void;
}

export interface CharacterRevealProps {
  characterId: string;
  name?: string;
  imageUrl?: string;
  bio?: string;
  revealed: boolean;
  onReveal?: () => void;
}

export interface StoryPortalProps {
  storyId: string;
  title: string;
  description: string;
  coverImageUrl?: string;
  progress?: number;
  branchCount?: number;
  onEnter?: () => void;
}
```

---

## Coordination with Agent A

### Week 1 (End): Deliver Prop Interfaces

**Your action:** Commit `types.ts` with ALL prop interfaces

**Agent A's action:** Reads your interfaces and converts to Zod schemas

### Week 2+: Commit Components as You Build

**Pattern:**
1. Build component (e.g., `InteractiveWorldMap.tsx`)
2. Export from `index.ts`
3. Commit with clear message
4. Update your status file

**Agent A will:** Read your committed code and add component to catalog

### Testing

Use **current Agent Bus** for initial testing:

```typescript
// Test InteractiveWorldMap via current Agent Bus
agentBus.emit({
  type: 'canvas_ui',
  component: 'InteractiveWorldMap',
  props: {
    worldId: 'test-world',
    locations: [
      { id: 'loc1', name: 'City Alpha', description: 'A bustling metropolis', position: { x: 0.3, y: 0.5 }, type: 'city' },
      { id: 'loc2', name: 'Research Facility', description: 'Top-secret lab', position: { x: 0.7, y: 0.6 }, type: 'facility' },
    ],
    connections: [
      { from: 'loc1', to: 'loc2', type: 'road' }
    ]
  },
  mountPoint: 'fullscreen',
});
```

By Week 3, Agent A will have migrated to json-render format (transparent to you).

---

## Status Tracking

**Create:** `.progress/016_phase3_world_space_status.md`

**Update daily:**

```markdown
# Phase 3: World Space Evolution - Status

**Agent:** B
**Week:** 1/3
**Last Updated:** 2026-01-XX

## Progress

### Week 1
- [x] Built InteractiveWorldMap component
- [x] Location visualization working
- [x] Hover previews implemented
- [x] Connection paths rendering
- [x] Defined all prop interfaces in types.ts
- [x] COMMITTED types.ts for Agent A

### Week 2
- [ ] Built TechArtifact component
- [ ] Built CharacterReveal component
- [ ] Built StoryPortal component
- [ ] Testing with current Agent Bus

### Week 3
- [ ] Per-world ambient audio
- [ ] Dynamic shader moods
- [ ] Particle effects
- [ ] Polish and edge cases

## Prop Interfaces Ready for Agent A:
- WorldMapProps (types.ts:15)
- TechArtifactProps (types.ts:30)
- CharacterRevealProps (types.ts:42)
- StoryPortalProps (types.ts:52)

## Blockers
- None

## Notes
- All components use current Agent Bus format
- Agent A will handle json-render migration transparently
```

---

## Files You'll Touch

**New Files (Create):**
- `apps/web/components/canvas/world/InteractiveWorldMap.tsx`
- `apps/web/components/canvas/world/TechArtifact.tsx`
- `apps/web/components/canvas/world/CharacterReveal.tsx`
- `apps/web/components/canvas/world/StoryPortal.tsx`
- `apps/web/components/canvas/world/types.ts` ⭐ **CRITICAL for Agent A**
- `apps/web/components/canvas/world/index.ts` (exports)
- `.progress/016_phase3_world_space_status.md`

**Modified Files:**
- None (all new components)

**Files Agent A Touches (NO CONFLICT):**
- `letta-code/src/agent-bus/` (protocol layer - different codebase)
- `apps/web/lib/agent-ui/` (catalog - different directory)

---

## Design Principles

### Spatial, Not Flat
- Locations have **position** on a map (not just listed)
- Tech artifacts are **3D objects** (not just cards)
- Characters exist **in space** (silhouettes, not text)

### Interactive, Not Static
- Hover reveals information
- Click explores deeper
- Everything responds to user action

### Mysterious, Not Obvious
- Characters hidden until revealed in stories
- Story portals hint at content without spoiling
- Information unfolds progressively

### Cinematic, Not Clinical
- Animations matter (framer-motion)
- Glow effects, shadows, depth
- Every interaction feels weighted

---

## Success Criteria

✅ **End of Week 3:**
- [ ] InteractiveWorldMap renders locations spatially
- [ ] TechArtifact shows 3D rotatable objects
- [ ] CharacterReveal has silhouette → full reveal flow
- [ ] StoryPortal displays stories as visual gateways
- [ ] All components have TypeScript interfaces
- [ ] All components work with current Agent Bus
- [ ] Agent A has added all to json-render catalog
- [ ] No breaking changes to existing Observatory

---

## Resources

- **Ultra Plan:** `.progress/013_20260110_immersive-ux-ultraplan.md`
- **Phase 3 Details:** Ultra Plan, "Layer 2: The World Space"
- **Coordination:** Ultra Plan, "Parallel Development Coordination Strategy"
- **Three.js docs:** https://threejs.org/docs/
- **React Three Fiber:** https://docs.pmnd.rs/react-three-fiber/
- **Framer Motion:** https://www.framer.com/motion/

---

## Questions? Issues?

Update your status file (`.progress/016_phase3_world_space_status.md`) with:
- Blockers
- Questions for Agent A
- Design decisions
- Deviations from plan

**Good luck, Agent B!** 🚀

---

## Bonus: Atmospheric Integration (Week 3)

### Per-World Ambient Audio

**File:** `apps/web/components/canvas/atmosphere/WorldAmbience.tsx`

```tsx
'use client';

import { useEffect, useRef } from 'react';

export interface WorldAmbienceProps {
  worldId: string;
  moodType: 'dark' | 'hopeful' | 'mysterious' | 'tense' | 'peaceful';
  volume?: number;  // 0-1
}

export function WorldAmbience({ worldId, moodType, volume = 0.5 }: WorldAmbienceProps) {
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    // Create procedural ambient sound based on mood
    const ctx = new AudioContext();
    audioContextRef.current = ctx;

    // Different frequency ranges per mood
    const moodConfig = {
      dark: { freq: 80, detune: 5 },
      hopeful: { freq: 440, detune: 10 },
      mysterious: { freq: 220, detune: 20 },
      tense: { freq: 120, detune: 30 },
      peaceful: { freq: 528, detune: 3 },
    };

    const config = moodConfig[moodType];

    // Oscillator for base tone
    const osc = ctx.createOscillator();
    osc.frequency.value = config.freq;

    // LFO for subtle modulation
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.5;

    const lfoGain = ctx.createGain();
    lfoGain.gain.value = config.detune;

    lfo.connect(lfoGain);
    lfoGain.connect(osc.detune);

    // Master gain
    const gain = ctx.createGain();
    gain.gain.value = volume * 0.1;  // Keep ambient quiet

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    lfo.start();

    return () => {
      osc.stop();
      lfo.stop();
      ctx.close();
    };
  }, [worldId, moodType, volume]);

  return null;  // Audio only, no visual
}
```

### Dynamic Shader Moods

**File:** `apps/web/components/canvas/atmosphere/DynamicShaderMood.tsx`

```tsx
'use client';

import { useEffect } from 'react';

export interface ShaderMoodProps {
  moodType: 'dark' | 'hopeful' | 'mysterious' | 'tense' | 'peaceful';
}

export function DynamicShaderMood({ moodType }: ShaderMoodProps) {
  useEffect(() => {
    // Update CSS variables for shader colors
    const moodColors = {
      dark: { primary: '#1a0a2e', secondary: '#000000' },
      hopeful: { primary: '#0a4d68', secondary: '#088395' },
      mysterious: { primary: '#16213e', secondary: '#533483' },
      tense: { primary: '#2d1b1b', secondary: '#8b0000' },
      peaceful: { primary: '#0f4c75', secondary: '#3282b8' },
    };

    const colors = moodColors[moodType];
    document.documentElement.style.setProperty('--shader-primary', colors.primary);
    document.documentElement.style.setProperty('--shader-secondary', colors.secondary);
  }, [moodType]);

  return null;  // Shader color only, no visual element
}
```

**Note:** Agent A will add these atmospheric components to catalog in Week 3.

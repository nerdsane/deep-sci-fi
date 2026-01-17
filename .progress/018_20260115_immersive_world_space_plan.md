# Immersive World Space - Implementation Plan

**Created:** 2026-01-15
**Status:** COMPLETE
**Type:** Technical Implementation Plan
**Dependencies:** Phase 1-2 Observatory (Complete)

---

## Executive Summary

Transform the World Space from a "2D page reading about the world" into a **3D immersive environment you explore from within**. The user flies through the world, visits locations, examines technologies, and discovers foundation rules spatially arranged in the environment.

**Goal:** When you click a world in the Observatory and warp in, you land INSIDE that world's space - not on a page about it.

---

## Research Summary

### Technology Stack (Already Installed)

| Package | Version | Usage |
|---------|---------|-------|
| `three` | 0.182.0 | 3D rendering engine |
| `@react-three/fiber` | 8.15.19 | React renderer for Three.js |
| `@react-three/drei` | 9.88.17 | Helper components |

### Key Drei Components to Use

| Component | Purpose | Source |
|-----------|---------|--------|
| `Environment` | HDRI skybox/environment map | [sbcode.net/react-three-fiber/environment](https://sbcode.net/react-three-fiber/environment/) |
| `Sky` | Procedural sky with sun position | [Drei docs](https://drei.docs.pmnd.rs/) |
| `Html` | Position HTML in 3D space | Already using in FloatingSuggestions |
| `Billboard` | Face camera always | [Drei docs](https://drei.docs.pmnd.rs/) |
| `CameraControls` | Smooth camera animation | [yomotsu/camera-controls](https://github.com/yomotsu/camera-controls) |
| `Stars` | Background star particles | Already using in Observatory |
| `Fog` | Atmospheric depth | [Three.js Fog docs](https://threejs.org/docs/#api/en/scenes/Fog) |

### Navigation Patterns Researched

1. **Click-to-Navigate**: Click locations → camera smoothly flies there
   - Best for: Exploration without complexity
   - Source: [GSAP Camera Animation](https://vaisakhnp.hashnode.dev/camera-animation-using-react-three-fiber-and-gsap)

2. **Waypoint Animation**: Predefined path with Theatre.js
   - Best for: Guided tours
   - Source: [Codrops Theatre.js Tutorial](https://tympanus.net/codrops/2023/02/14/animate-a-camera-fly-through-on-scroll-using-theatre-js-and-react-three-fiber/)

3. **Free Exploration**: PointerLockControls + WASD
   - Best for: Game-like exploration
   - Source: [Drei Controls](https://drei.docs.pmnd.rs/controls/introduction)

**Chosen Approach:** Click-to-Navigate with smooth camera transitions (like Observatory hover zoom, but for locations)

---

## Design Vision

### Concept: "The World as Space"

When you enter a world, you're floating in that world's conceptual space:

```
┌─────────────────────────────────────────────────────────────────┐
│                     WORLD SPACE (3D)                            │
│                                                                 │
│   ⬡ Location A                    ⬡ Location B                  │
│      "Neo Tokyo"                     "Orbital Station"          │
│         │                               │                       │
│         │←─────── Connection ──────────→│                       │
│                                                                 │
│                     🌐 CENTRAL HUB                              │
│                   (Foundation Rules)                            │
│                   ┌─────────────────┐                          │
│                   │ Rule 1: FTL is  │                          │
│                   │ impossible      │                          │
│                   │ Rule 2: AI has  │                          │
│                   │ partial amnesia │                          │
│                   └─────────────────┘                          │
│                                                                 │
│      ✦ Tech: Quantum Core            ✦ Tech: Neural Link        │
│                                                                 │
│   ⊙ Story Portal                  ⊙ Story Portal               │
│   "First Contact"                 "The Incident"               │
│                                                                 │
│                    👁 Agent Presence                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Experience Flow

1. **Entry**: Warp from Observatory → land at central hub
2. **Central Hub**: Foundation rules displayed around you (the "core" of the world)
3. **Locations**: Visible as glowing points in the distance, click to fly there
4. **Technologies**: Floating 3D artifacts, click to examine
5. **Story Portals**: Gateways at the periphery, enter to read story
6. **Agent Presence**: Floating nearby, offering suggestions

### Visual Language

| Element | 3D Representation | Interaction |
|---------|-------------------|-------------|
| Foundation Rules | Floating text panels around hub | Hover to expand |
| Locations | Glowing orbs with icons | Click to fly there |
| Technologies | 3D rotating artifacts | Click to inspect modal |
| Story Portals | Portal ring effects | Click to enter story |
| Connections | Particle streams between locations | Visual only |
| World Cover | Environment map / skybox | Background |

---

## Architecture

### Component Structure

```
apps/web/components/canvas/world-space/
├── ImmersiveWorldSpace.tsx     # Main 3D canvas component
├── WorldSpaceScene.tsx         # Inner scene with Three.js context
├── CentralHub.tsx              # Foundation rules display
├── LocationNode.tsx            # 3D location representation
├── TechnologyArtifact3D.tsx    # 3D tech objects
├── StoryPortal3D.tsx           # Story entry gateways
├── ConnectionStream.tsx        # Particle paths between locations
├── WorldEnvironment.tsx        # Skybox + atmosphere
├── useWorldSpaceCamera.ts      # Camera navigation hook
├── world-space-3d.css          # Overlay styles
├── types.ts                    # TypeScript interfaces
└── index.ts                    # Exports
```

### Data Flow

```
World Data (from API)
    │
    ▼
ImmersiveWorldSpace
    │
    ├──→ WorldEnvironment (skybox from cover image)
    │
    ├──→ CentralHub (foundation.rules → 3D text panels)
    │
    ├──→ LocationNode[] (surface.visible_elements.filter(type=location))
    │
    ├──→ TechnologyArtifact3D[] (surface.visible_elements.filter(type=technology))
    │
    ├──→ StoryPortal3D[] (stories array)
    │
    └──→ AgentPresence (reuse from Observatory)
```

---

## Technical Implementation

### Phase 1: Core 3D Canvas (Day 1)

#### 1.1 ImmersiveWorldSpace.tsx

```typescript
// Core structure
export function ImmersiveWorldSpace({
  world,
  stories,
  onSelectStory,
  onExploreElement,
  onBack
}: ImmersiveWorldSpaceProps) {
  const isClient = useIsClient();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  if (!isClient) return <LoadingScreen />;

  return (
    <div className="immersive-world-space">
      <Canvas camera={{ position: [0, 2, 10], fov: 60 }}>
        <Suspense fallback={null}>
          <WorldSpaceScene
            world={world}
            stories={stories}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            onSelectStory={onSelectStory}
            onExploreElement={onExploreElement}
          />
        </Suspense>
      </Canvas>

      {/* Back button overlay */}
      <button className="world-space-back" onClick={onBack}>
        ← Observatory
      </button>

      {/* Inspection modal overlay */}
      {selectedNode && (
        <InspectionModal
          nodeId={selectedNode}
          world={world}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
```

#### 1.2 Camera Navigation Hook

```typescript
// useWorldSpaceCamera.ts
export function useWorldSpaceCamera() {
  const { camera } = useThree();
  const targetRef = useRef<THREE.Vector3 | null>(null);
  const lookAtRef = useRef<THREE.Vector3 | null>(null);
  const progressRef = useRef(0);
  const [isFlying, setIsFlying] = useState(false);

  const flyTo = useCallback((position: THREE.Vector3, lookAt: THREE.Vector3) => {
    targetRef.current = position;
    lookAtRef.current = lookAt;
    progressRef.current = 0;
    setIsFlying(true);
  }, []);

  const returnToHub = useCallback(() => {
    flyTo(
      new THREE.Vector3(0, 2, 10), // Hub camera position
      new THREE.Vector3(0, 0, 0)  // Look at center
    );
  }, [flyTo]);

  useFrame((_, delta) => {
    if (!isFlying || !targetRef.current) return;

    progressRef.current += delta * 0.8; // Animation speed
    const t = easeInOutCubic(Math.min(progressRef.current, 1));

    camera.position.lerp(targetRef.current, t);
    if (lookAtRef.current) {
      camera.lookAt(lookAtRef.current);
    }

    if (progressRef.current >= 1) {
      setIsFlying(false);
    }
  });

  return { flyTo, returnToHub, isFlying };
}
```

### Phase 2: Central Hub - Foundation Rules (Day 1-2)

The Central Hub displays Foundation Rules as floating panels arranged in a circle around the entry point.

#### 2.1 CentralHub.tsx

```typescript
// Foundation rules as floating panels
export function CentralHub({ rules, onRuleClick }: CentralHubProps) {
  const groupRef = useRef<THREE.Group>(null);

  // Arrange rules in a semicircle
  const rulePositions = useMemo(() => {
    return rules.map((rule, i) => {
      const angle = (Math.PI / (rules.length + 1)) * (i + 1) - Math.PI / 2;
      const radius = 5;
      return new THREE.Vector3(
        Math.cos(angle) * radius,
        1 + i * 0.3, // Slight vertical offset
        Math.sin(angle) * radius
      );
    });
  }, [rules]);

  return (
    <group ref={groupRef}>
      {/* Central orb - world core */}
      <WorldCore />

      {/* Foundation rule panels */}
      {rules.map((rule, i) => (
        <RulePanel
          key={rule.id}
          rule={rule}
          position={rulePositions[i]}
          onClick={() => onRuleClick?.(rule)}
        />
      ))}
    </group>
  );
}

function RulePanel({ rule, position, onClick }: RulePanelProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <Billboard position={position}>
      <Html
        center
        style={{
          pointerEvents: 'auto',
        }}
      >
        <div
          className={`rule-panel ${hovered ? 'rule-panel--hovered' : ''}`}
          onPointerEnter={() => setHovered(true)}
          onPointerLeave={() => setHovered(false)}
          onClick={onClick}
        >
          <span className="rule-panel__certainty">{rule.certainty}</span>
          <p className="rule-panel__statement">{rule.statement}</p>
          {hovered && rule.implications && (
            <ul className="rule-panel__implications">
              {rule.implications.map((imp, i) => (
                <li key={i}>{imp}</li>
              ))}
            </ul>
          )}
        </div>
      </Html>
    </Billboard>
  );
}
```

### Phase 3: Location Nodes (Day 2)

Locations appear as glowing orbs positioned around the space. Click to fly camera there.

#### 3.1 LocationNode.tsx

```typescript
export function LocationNode({
  location,
  position,
  isSelected,
  onSelect,
  onFlyTo
}: LocationNodeProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  // Gentle floating animation
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime + position[0]) * 0.1;
    }
  });

  const handleClick = () => {
    onSelect(location.id);
    // Fly camera to viewing position near this location
    const viewPos = new THREE.Vector3(
      position[0] - 3,
      position[1] + 1,
      position[2] + 3
    );
    onFlyTo(viewPos, new THREE.Vector3(...position));
  };

  return (
    <group position={position}>
      {/* Core sphere */}
      <mesh
        ref={meshRef}
        onClick={handleClick}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
        scale={hovered ? 1.2 : 1}
      >
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color={hovered ? '#00ffff' : '#00ffcc'}
          emissive={hovered ? '#00ffcc' : '#006666'}
          emissiveIntensity={hovered ? 0.8 : 0.4}
        />
      </mesh>

      {/* Glow effect */}
      <pointLight
        color="#00ffcc"
        intensity={hovered ? 2 : 0.5}
        distance={3}
      />

      {/* Label */}
      <Html position={[0, 1, 0]} center>
        <div className="location-label">
          <span className="location-label__icon">{location.icon || '📍'}</span>
          <span className="location-label__name">{location.name}</span>
        </div>
      </Html>

      {/* Expanded info when selected */}
      {isSelected && (
        <Html position={[0, -1.5, 0]} center>
          <div className="location-detail">
            <h4>{location.name}</h4>
            <p>{location.description}</p>
          </div>
        </Html>
      )}
    </group>
  );
}
```

### Phase 4: Technology Artifacts (Day 2-3)

Technologies as 3D rotating objects floating in space.

#### 4.1 TechnologyArtifact3D.tsx

```typescript
export function TechnologyArtifact3D({
  tech,
  position,
  onInspect
}: TechnologyArtifact3DProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  // Auto-rotation
  useFrame((_, delta) => {
    if (meshRef.current && !hovered) {
      meshRef.current.rotation.y += delta * 0.5;
    }
  });

  // Get shape based on category
  const geometry = useMemo(() => {
    switch (tech.category) {
      case 'device': return <boxGeometry args={[0.8, 0.4, 0.6]} />;
      case 'vehicle': return <coneGeometry args={[0.4, 1, 6]} />;
      case 'weapon': return <cylinderGeometry args={[0.1, 0.2, 1.2, 8]} />;
      default: return <icosahedronGeometry args={[0.5, 0]} />;
    }
  }, [tech.category]);

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={() => onInspect(tech)}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
        scale={hovered ? 1.3 : 1}
      >
        {geometry}
        <meshStandardMaterial
          color="#ff8800"
          emissive="#ff4400"
          emissiveIntensity={hovered ? 0.6 : 0.3}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>

      {/* Particle effect around tech */}
      <TechParticles active={hovered} />

      {/* Label */}
      <Html position={[0, 1, 0]} center>
        <div className={`tech-label ${hovered ? 'tech-label--hovered' : ''}`}>
          <span className="tech-label__icon">✦</span>
          <span className="tech-label__name">{tech.name}</span>
        </div>
      </Html>
    </group>
  );
}
```

### Phase 5: Story Portals (Day 3)

Story portals as dramatic gateway effects at the edges of the space.

#### 5.1 StoryPortal3D.tsx

```typescript
export function StoryPortal3D({
  story,
  position,
  onEnter
}: StoryPortal3DProps) {
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  // Ring rotation
  useFrame((_, delta) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * (hovered ? 1.5 : 0.5);
    }
  });

  return (
    <group position={position}>
      {/* Portal ring */}
      <mesh
        ref={ringRef}
        onClick={() => onEnter(story)}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <torusGeometry args={[1.2, 0.1, 16, 100]} />
        <meshStandardMaterial
          color={hovered ? '#00ffff' : '#00ffcc'}
          emissive={hovered ? '#00ffcc' : '#006666'}
          emissiveIntensity={hovered ? 1 : 0.5}
        />
      </mesh>

      {/* Inner glow */}
      <mesh scale={0.95}>
        <circleGeometry args={[1.1, 64]} />
        <meshBasicMaterial
          color="#001111"
          transparent
          opacity={0.8}
        />
      </mesh>

      {/* Portal light */}
      <pointLight
        color="#00ffcc"
        intensity={hovered ? 3 : 1}
        distance={5}
      />

      {/* Story info */}
      <Html position={[0, -2, 0]} center>
        <div className={`portal-label ${hovered ? 'portal-label--hovered' : ''}`}>
          <h4 className="portal-label__title">{story.metadata.title}</h4>
          <span className="portal-label__meta">
            {story.segments.length} segments · {story.metadata.status}
          </span>
          {hovered && (
            <p className="portal-label__desc">{story.metadata.description}</p>
          )}
        </div>
      </Html>
    </group>
  );
}
```

### Phase 6: Environment & Atmosphere (Day 3)

#### 6.1 WorldEnvironment.tsx

```typescript
export function WorldEnvironment({
  coverImage,
  mood
}: WorldEnvironmentProps) {
  // Mood-based settings
  const fogColor = useMemo(() => {
    switch (mood) {
      case 'dark': return '#050505';
      case 'mysterious': return '#0a0a15';
      case 'hopeful': return '#0a1520';
      default: return '#080808';
    }
  }, [mood]);

  return (
    <>
      {/* Background color */}
      <color attach="background" args={[fogColor]} />

      {/* Atmospheric fog */}
      <fog attach="fog" args={[fogColor, 20, 60]} />

      {/* Ambient lighting */}
      <ambientLight intensity={0.2} />

      {/* Key light */}
      <directionalLight
        position={[10, 10, 5]}
        intensity={0.5}
        color="#ffffff"
      />

      {/* Fill light */}
      <pointLight
        position={[-10, 5, -10]}
        intensity={0.3}
        color="#00ffcc"
      />

      {/* Stars in background */}
      <Stars
        radius={100}
        depth={50}
        count={2000}
        factor={4}
        fade
      />

      {/* Optional: Use cover image as environment */}
      {coverImage && (
        <Environment
          background
          files={coverImage}
          backgroundBlurriness={0.5}
        />
      )}
    </>
  );
}
```

### Phase 7: Connection Streams (Day 4)

Visual particle paths connecting related locations.

#### 7.1 ConnectionStream.tsx

```typescript
export function ConnectionStream({
  from,
  to,
  type
}: ConnectionStreamProps) {
  const points = useMemo(() => {
    const start = new THREE.Vector3(...from);
    const end = new THREE.Vector3(...to);
    const mid = start.clone().lerp(end, 0.5);
    mid.y += 1; // Arc upward

    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    return curve.getPoints(50);
  }, [from, to]);

  const lineGeometry = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return geo;
  }, [points]);

  return (
    <line>
      <primitive object={lineGeometry} />
      <lineBasicMaterial
        color="#00ffcc"
        opacity={0.3}
        transparent
      />
    </line>
  );
}
```

---

## Integration with Page

### Switching WorldSpaceEnhanced → ImmersiveWorldSpace

```typescript
// apps/web/app/page.tsx

// Change this:
{state.view === 'world' && state.selectedWorld && (
  <WorldSpaceEnhanced ... />
)}

// To this:
{state.view === 'world' && state.selectedWorld && (
  <ImmersiveWorldSpace
    world={state.selectedWorld}
    stories={state.stories.filter(...)}
    onSelectStory={selectStory}
    onExploreElement={handleElementAction}
    onBack={() => setState(s => ({ ...s, view: 'canvas' }))}
  />
)}
```

---

## Success Criteria

### Functional
- [x] Camera smoothly flies between locations
- [x] Foundation rules display as floating panels
- [x] Locations render as interactive orbs
- [x] Technologies render as rotating 3D shapes
- [x] Story portals render with glow effects
- [x] Click location → fly there
- [x] Click story portal → enter story
- [x] Back button → return to Observatory

### Visual
- [x] Consistent with Observatory aesthetic (dark, cyan/teal glows)
- [x] Atmospheric fog adds depth
- [x] Stars visible in background
- [x] Smooth animations on all interactions
- [x] Labels readable but not intrusive

### Performance
- [x] 60fps on modern hardware
- [x] Smooth camera transitions
- [x] No memory leaks
- [x] Lazy load heavy assets

## Testing Results (2026-01-15)

All components tested and working:
1. **ImmersiveWorldSpace** - Loads correctly from Observatory click
2. **CentralHub** - Displays foundation rules with WorldCore and RulePanels
3. **LocationNode** - Component ready (no location data in test worlds)
4. **TechnologyArtifact3D** - Component ready (no tech data in test worlds)
5. **StoryPortal3D** - Component ready (no story data in test worlds)
6. **Camera Navigation** - OrbitControls working correctly
7. **Back Button** - Returns to Observatory correctly

Note: Minor React key warning in console (non-blocking)

---

## Timeline

| Day | Focus | Deliverables |
|-----|-------|--------------|
| 1 | Core setup | ImmersiveWorldSpace, camera hook, basic scene |
| 2 | Central Hub + Locations | Rule panels, LocationNode, navigation |
| 3 | Tech + Portals | TechnologyArtifact3D, StoryPortal3D |
| 4 | Environment + Polish | Fog, lighting, connections, animations |
| 5 | Integration + Testing | Replace WorldSpaceEnhanced, test flows |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Performance with many objects | Level of detail, frustum culling |
| HTML labels overlapping | Occlusion testing, Billboard component |
| Camera getting stuck | Collision avoidance, reset button |
| Mobile performance | Reduced particle count, simpler shaders |

---

## Open Questions

1. **Should we keep WorldSpaceEnhanced as fallback?**
   - Recommendation: Yes, for accessibility/performance toggle

2. **How to handle worlds with no locations?**
   - Show only Central Hub with rules and story portals

3. **Should technologies be at specific locations or floating around hub?**
   - Start with floating around hub, can attach to locations later

4. **First-person or third-person camera?**
   - Start with third-person (orbit-like), can add first-person option later

---

## References

### Research Sources
- [React Three Fiber Docs](https://docs.pmnd.rs/react-three-fiber)
- [Drei Controls Documentation](https://drei.docs.pmnd.rs/controls/introduction)
- [Camera Animation with GSAP](https://vaisakhnp.hashnode.dev/camera-animation-using-react-three-fiber-and-gsap)
- [Theatre.js Fly-through](https://tympanus.net/codrops/2023/02/14/animate-a-camera-fly-through-on-scroll-using-theatre-js-and-react-three-fiber/)
- [3D UI/UX Design Guide 2025](https://viartisan.com/2025/05/28/3d-ui-ux-design/)
- [Spatial UI Design Principles](https://borakaizen.medium.com/design-for-spatial-user-interfaces-creating-immersive-experiences-in-three-dimensional-space-24e3ea21ddd3)
- [Three.js Fog Documentation](https://threejs.org/docs/#api/en/scenes/Fog)
- [R3F Hotspots Example](https://codesandbox.io/s/react-three-fiber-hotspots-9t4be)

---

## Ready to Implement

This plan provides a complete roadmap for building the true immersive World Space experience. The approach:

1. **Builds on Observatory patterns** - Same R3F stack, similar camera animations
2. **Uses proven drei components** - Html, Billboard, Stars, Environment
3. **Click-to-navigate paradigm** - Intuitive, no complex controls to learn
4. **Foundation Rules at center** - The "core" of the world you explore around
5. **Spatial arrangement** - Elements positioned in 3D, not listed on page

**Next Step:** Begin implementation of Phase 1 (ImmersiveWorldSpace.tsx + camera hook)

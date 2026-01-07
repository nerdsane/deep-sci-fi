# Component Strategy: Agent-Composable UI with Your Styling

## Current State Analysis

### ✅ What You Have
- **Beautiful custom design system** - Pure black foundation, neon cyan/purple accents, minimalist terminal aesthetic
- **Clean CSS architecture** - CSS variables, 8px spacing scale, typography system
- **React 18.3.1** - Already set up for component-based architecture
- **Zero component library dependencies** - Clean slate for choosing the right approach

### 🎯 What You Want
- Agent can compose UI declaratively (via `canvas_ui` tool)
- Components match your existing neon cyberpunk aesthetic
- Don't reinvent the wheel (reuse proven patterns)
- Composable, flexible system

## Recommendation: **Radix UI Primitives + Your Custom Styling**

Based on research and your requirements, here's the optimal approach:

### Why Radix UI?

**Perfect fit for your use case:**
1. **Unstyled primitives** - Zero style conflicts, 100% your aesthetic
2. **Behavior + Accessibility** - You get the hard parts (keyboard nav, ARIA, focus management)
3. **Composable API** - `asChild` prop and render props support declarative JSON-driven composition
4. **Proven foundation** - Powers shadcn/ui and many design systems
5. **React 18 compatible** - Works with your existing setup

**Key advantages for agent-controlled UI:**
- Agent specifies components as data → Radix handles behavior → Your CSS handles styling
- No style overrides needed (it's headless)
- `data-state` attributes make styling interactions trivial
- Composable slots align perfectly with JSON component definitions

### Components You'll Need

Radix provides 30+ primitives. For DSF Phase 1, install these:

```bash
bun add @radix-ui/react-dialog        # Modal
bun add @radix-ui/react-popover       # Popovers/tooltips
bun add @radix-ui/react-tabs          # Tabs
bun add @radix-ui/react-accordion     # Accordion
bun add @radix-ui/react-separator     # Dividers
bun add @radix-ui/react-scroll-area   # Custom scrollbars
bun add @radix-ui/react-slider        # Slider input
bun add @radix-ui/react-switch        # Toggle
bun add @radix-ui/react-select        # Select dropdown
```

## Architecture: JSON → Radix → Your Styles

### Component Mapping Strategy

```typescript
// Agent specifies components declaratively
const componentSpec = {
  type: "Dialog",
  trigger: { type: "Button", label: "Open Story" },
  content: {
    type: "Stack",
    children: [
      { type: "Text", content: "Chapter 1", variant: "heading" },
      { type: "Markdown", content: "The city breathed..." }
    ]
  }
}

// Your renderer maps to Radix + your styles
<Dialog.Root>
  <Dialog.Trigger asChild>
    <button className="action-button action-button-primary">
      Open Story
    </button>
  </Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Overlay className="dialog-overlay" />
    <Dialog.Content className="dialog-content">
      {/* Rendered content */}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

### Styling Approach

**Keep your existing CSS, extend for Radix states:**

```css
/* Add to your styles.css */

/* Dialog - matches your neon aesthetic */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  animation: fadeIn 0.2s ease;
}

.dialog-content {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--bg-secondary);
  border: 1px solid var(--border-medium);
  border-top: 2px solid var(--neon-cyan);
  padding: var(--space-5);
  max-width: 600px;
  width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 0 40px rgba(0, 255, 204, 0.2);
  animation: slideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Radix provides data-state attributes for interactions */
.dialog-content[data-state="open"] {
  animation: slideIn 0.3s ease;
}

.dialog-content[data-state="closed"] {
  animation: slideOut 0.2s ease;
}

/* Tabs - your style */
.tabs-root {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.tabs-list {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--border-subtle);
}

.tabs-trigger {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.tabs-trigger:hover {
  color: var(--text-primary);
}

.tabs-trigger[data-state="active"] {
  color: var(--neon-cyan);
  border-bottom-color: var(--neon-cyan);
}

.tabs-content {
  padding: var(--space-3) 0;
}

/* Slider - matches your neon accents */
.slider-root {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  height: 20px;
  user-select: none;
  touch-action: none;
}

.slider-track {
  position: relative;
  flex-grow: 1;
  height: 2px;
  background: var(--border-medium);
}

.slider-range {
  position: absolute;
  height: 100%;
  background: var(--neon-cyan);
  box-shadow: 0 0 8px rgba(0, 255, 204, 0.5);
}

.slider-thumb {
  display: block;
  width: 16px;
  height: 16px;
  background: var(--neon-cyan);
  border: 2px solid var(--bg-primary);
  border-radius: 50%;
  box-shadow: 0 0 12px rgba(0, 255, 204, 0.6);
  transition: all 0.2s ease;
}

.slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 0 16px rgba(0, 255, 204, 0.8);
}

.slider-thumb[data-state="active"] {
  transform: scale(1.3);
}

/* Switch - your aesthetic */
.switch-root {
  all: unset;
  width: 42px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  position: relative;
  cursor: pointer;
  transition: all 0.2s ease;
}

.switch-root[data-state="checked"] {
  background: rgba(0, 255, 204, 0.2);
  border-color: var(--neon-cyan);
  box-shadow: 0 0 12px rgba(0, 255, 204, 0.3);
}

.switch-thumb {
  display: block;
  width: 18px;
  height: 18px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: transform 0.2s ease;
  transform: translateX(2px);
}

.switch-root[data-state="checked"] .switch-thumb {
  transform: translateX(20px);
  background: var(--neon-cyan);
  box-shadow: 0 0 8px rgba(0, 255, 204, 0.6);
}
```

## Implementation Plan

### Phase 1: Foundation Components (Week 1)

**Goal:** Build 8 core styled Radix components matching your aesthetic

#### Day 1: Setup & Layout Components
```bash
cd letta-code
bun add @radix-ui/react-tabs @radix-ui/react-separator @radix-ui/react-scroll-area
```

Create `src/canvas/components/radix/` directory:

```
src/canvas/components/radix/
├── Dialog.tsx          # Modal overlays
├── Tabs.tsx            # Tab navigation
├── Separator.tsx       # Dividers
└── styles.css          # Radix-specific styles
```

**Dialog.tsx:**
```typescript
import * as Dialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

interface DSFDialogProps {
  trigger: ReactNode;
  title?: string;
  description?: string;
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function DSFDialog({
  trigger,
  title,
  description,
  children,
  open,
  onOpenChange
}: DSFDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Trigger asChild>
        {trigger}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          {title && (
            <Dialog.Title className="dialog-title">
              {title}
            </Dialog.Title>
          )}
          {description && (
            <Dialog.Description className="dialog-description">
              {description}
            </Dialog.Description>
          )}
          {children}
          <Dialog.Close asChild>
            <button className="dialog-close" aria-label="Close">
              ×
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

**Tabs.tsx:**
```typescript
import * as Tabs from '@radix-ui/react-tabs';

interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface DSFTabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onTabChange?: (value: string) => void;
}

export function DSFTabs({ tabs, defaultTab, onTabChange }: DSFTabsProps) {
  return (
    <Tabs.Root
      className="tabs-root"
      defaultValue={defaultTab || tabs[0]?.id}
      onValueChange={onTabChange}
    >
      <Tabs.List className="tabs-list">
        {tabs.map((tab) => (
          <Tabs.Trigger key={tab.id} value={tab.id} className="tabs-trigger">
            {tab.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {tabs.map((tab) => (
        <Tabs.Content key={tab.id} value={tab.id} className="tabs-content">
          {tab.content}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
```

#### Day 2: Interactive Components
```bash
bun add @radix-ui/react-slider @radix-ui/react-switch @radix-ui/react-select
```

Build: Slider, Switch, Select with your neon styling

#### Day 3-4: Component Renderer

Create `src/canvas/components/DynamicRenderer.tsx`:

```typescript
import type { ComponentSpec } from '../../types/canvas';
import { DSFDialog } from './radix/Dialog';
import { DSFTabs } from './radix/Tabs';
import { DSFSlider } from './radix/Slider';
import { DSFSwitch } from './radix/Switch';
// ... import your existing components (Text, Markdown, etc.)

interface RendererProps {
  spec: ComponentSpec;
  onInteraction: (id: string, type: string, data: any) => void;
}

export function DynamicRenderer({ spec, onInteraction }: RendererProps) {
  const { type, id, props } = spec;

  // Map JSON spec to actual components
  switch (type) {
    case 'Dialog':
      return (
        <DSFDialog
          trigger={props.trigger ? <DynamicRenderer spec={props.trigger} onInteraction={onInteraction} /> : null}
          title={props.title}
          open={props.open}
          onOpenChange={(open) => onInteraction(id, 'dialog_change', { open })}
        >
          {props.children && <DynamicRenderer spec={props.children} onInteraction={onInteraction} />}
        </DSFDialog>
      );

    case 'Tabs':
      return (
        <DSFTabs
          tabs={props.tabs.map((tab: any) => ({
            ...tab,
            content: <DynamicRenderer spec={tab.content} onInteraction={onInteraction} />
          }))}
          onTabChange={(value) => onInteraction(id, 'tab_change', { value })}
        />
      );

    case 'Slider':
      return (
        <DSFSlider
          value={props.value}
          min={props.min}
          max={props.max}
          step={props.step}
          onValueChange={(value) => onInteraction(id, 'slider_change', { value })}
        />
      );

    // ... other component types

    case 'Stack':
      return (
        <div className="stack" style={{ gap: props.spacing || 16 }}>
          {props.children?.map((child: ComponentSpec, i: number) => (
            <DynamicRenderer key={i} spec={child} onInteraction={onInteraction} />
          ))}
        </div>
      );

    default:
      return <div className="unknown-component">Unknown: {type}</div>;
  }
}
```

#### Day 5: Testing & Integration

Test agent-to-canvas flow:

```typescript
// Agent calls canvas_ui:
canvas_ui({
  operation: "render",
  component_id: "story-browser",
  definition: {
    type: "Tabs",
    id: "story-tabs",
    props: {
      tabs: [
        {
          id: "text",
          label: "Story",
          content: {
            type: "Markdown",
            props: { content: "Chapter 1..." }
          }
        },
        {
          id: "images",
          label: "Gallery",
          content: {
            type: "Gallery",
            props: { items: ["asset-1", "asset-2"] }
          }
        }
      ]
    }
  }
})
```

Canvas renders with your neon aesthetic automatically!

### Phase 2: Advanced Components (Week 2)

Add:
- Accordion (collapsible sections)
- Popover (contextual info)
- Select (dropdown menus)
- ScrollArea (custom scrollbars matching your theme)

### Phase 3: Story-Specific Components (Week 3)

Build domain-specific wrappers:
- StoryExplorer (Tabs + Gallery + Timeline)
- WorldBrowser (Accordion of rules/elements)
- SegmentViewer (ScrollArea + Markdown + asset embeds)

## Comparison: Radix vs Alternatives

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Radix UI** (Recommended) | ✅ Unstyled (zero conflicts)<br>✅ Behavior + A11y handled<br>✅ Composable API<br>✅ Proven (powers shadcn)<br>✅ 30+ components | ⚠️ Need to style each (but you want this)<br>⚠️ Learning curve | **Best fit** |
| **shadcn/ui** | ✅ Pre-styled<br>✅ Copy-paste ready<br>✅ Tailwind integration | ❌ Opinionated styling (conflicts with yours)<br>❌ Harder to customize deeply<br>❌ Not built for agent JSON specs | ❌ Wrong choice |
| **Headless UI** | ✅ Unstyled<br>✅ Tailwind focused | ⚠️ Smaller ecosystem<br>⚠️ Less composable than Radix | ⚠️ OK alternative |
| **Pure custom** | ✅ Total control | ❌ Reinvent keyboard nav<br>❌ Reinvent accessibility<br>❌ Reinvent focus management | ❌ Too much work |

## Migration Path

### Immediate (This Week)
1. ✅ Install Radix primitives for Phase 1 components
2. ✅ Create styled wrappers in `components/radix/`
3. ✅ Build DynamicRenderer with component mapping
4. ✅ Test with simple agent-specified layouts

### Short-term (Next 2 Weeks)
1. Add remaining Radix components as needed
2. Refine styling to perfectly match your aesthetic
3. Build story-specific composite components
4. Integrate with Agent Bus for full bidirectional flow

### Long-term
- Consider extracting your styled Radix components as internal library
- Document component specs for agent reference
- Build component gallery/playground for testing

## Code Organization

```
letta-code/src/canvas/
├── components/
│   ├── radix/              # Styled Radix wrappers
│   │   ├── Dialog.tsx
│   │   ├── Tabs.tsx
│   │   ├── Slider.tsx
│   │   ├── Switch.tsx
│   │   ├── Select.tsx
│   │   └── styles.css      # Radix-specific styles
│   ├── primitives/         # Basic components (existing)
│   │   ├── Text.tsx
│   │   ├── Markdown.tsx
│   │   └── Image.tsx
│   ├── layouts/            # Layout components (existing)
│   │   ├── Stack.tsx
│   │   ├── Grid.tsx
│   │   └── Split.tsx
│   └── DynamicRenderer.tsx # JSON → Component mapper
├── styles.css              # Your existing styles (keep!)
└── app.tsx                 # Main app
```

## Benefits Summary

**Why this approach wins:**

1. **Keep your aesthetic 100%** - Radix has zero styles, you apply yours
2. **Don't reinvent behavior** - Keyboard nav, ARIA, focus management solved
3. **Agent-friendly** - Radix's composable API maps perfectly to JSON specs
4. **Battle-tested** - Powers shadcn/ui and many production apps
5. **Incremental adoption** - Add components as needed, no big rewrite
6. **Future-proof** - Well-maintained, React 18+, growing ecosystem

**Your neon cyberpunk design stays intact**, you just get the hard parts (accessibility, state management, animations) for free.

## Next Steps

1. **Install Radix primitives** - Start with Dialog, Tabs, Slider, Switch
2. **Style one component** - Pick Dialog, style it with your CSS, test
3. **Build DynamicRenderer** - Map JSON specs to Radix components
4. **Test with agent** - Have agent create a simple Dialog via canvas_ui
5. **Iterate** - Add more components, refine styling, expand renderer

**Estimated effort:** 1-2 weeks for Phase 1 (8 core components + renderer)

---

## Questions?

- **"Will Radix conflict with my styles?"** - No! It's completely unstyled.
- **"Do I need Tailwind?"** - Nope! Your existing CSS works perfectly.
- **"Can I use my existing components?"** - Yes! Radix for complex interactions, yours for simple content.
- **"What if I need a component Radix doesn't have?"** - Build custom and add to your library.

You get best of both worlds: **your unique aesthetic + proven interactive components**.

# Radix UI Integration: Quick Start Guide

Get your first agent-composable Radix component working in 30 minutes.

## Prerequisites

- Your current canvas setup (React 18.3.1, custom CSS)
- Agent Bus implementation (from dynamic-canvas-ux-vision.md)
- canvas_ui tool (from technical-specs/canvas-ui-tool.md)

## Step 1: Install Radix (2 minutes)

```bash
cd letta-code

# Install first batch - layout & interaction
bun add @radix-ui/react-dialog
bun add @radix-ui/react-tabs
bun add @radix-ui/react-slider
bun add @radix-ui/react-switch
```

## Step 2: Create Your First Styled Component - Dialog (10 minutes)

Create `src/canvas/components/radix/Dialog.tsx`:

```typescript
import * as Dialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

interface DSFDialogProps {
  trigger?: ReactNode;
  title?: string;
  description?: string;
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Dialog component styled with DSF's neon cyberpunk aesthetic
 * Wraps Radix UI Dialog primitive
 */
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
      {trigger && (
        <Dialog.Trigger asChild>
          {trigger}
        </Dialog.Trigger>
      )}
      <Dialog.Portal>
        <Dialog.Overlay className="dsf-dialog-overlay" />
        <Dialog.Content className="dsf-dialog-content">
          {title && (
            <Dialog.Title className="dsf-dialog-title">
              {title}
            </Dialog.Title>
          )}
          {description && (
            <Dialog.Description className="dsf-dialog-description">
              {description}
            </Dialog.Description>
          )}
          <div className="dsf-dialog-body">
            {children}
          </div>
          <Dialog.Close asChild>
            <button className="dsf-dialog-close" aria-label="Close">
              ×
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

## Step 3: Add Radix Styles to Your CSS (5 minutes)

Add to `src/canvas/styles.css`:

```css
/* ============================================================================
   Radix UI - DSF Styled Components
   ============================================================================ */

/* Dialog - Neon Cyberpunk Modal */
@keyframes dialogOverlayShow {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes dialogContentShow {
  from {
    opacity: 0;
    transform: translate(-50%, -48%) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

@keyframes dialogContentHide {
  from {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  to {
    opacity: 0;
    transform: translate(-50%, -48%) scale(0.96);
  }
}

.dsf-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  z-index: 1000;
  animation: dialogOverlayShow 0.2s ease;
}

.dsf-dialog-content {
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
  z-index: 1001;
  box-shadow: 0 0 40px rgba(0, 255, 204, 0.2);
  animation: dialogContentShow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.dsf-dialog-content[data-state="closed"] {
  animation: dialogContentHide 0.2s ease;
}

.dsf-dialog-title {
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
  position: relative;
}

.dsf-dialog-title::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 60px;
  height: 2px;
  background: var(--neon-cyan);
  box-shadow: 0 0 8px rgba(0, 255, 204, 0.5);
}

.dsf-dialog-description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
  line-height: 1.6;
}

.dsf-dialog-body {
  /* Container for dialog content */
}

.dsf-dialog-close {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: var(--text-2xl);
  font-weight: 300;
  line-height: 1;
  transition: all 0.2s ease;
  font-family: var(--font-mono);
}

.dsf-dialog-close:hover {
  background: rgba(255, 0, 0, 0.1);
  border-color: rgba(255, 0, 0, 0.5);
  color: #ff4444;
}

/* Scrollbar for dialog content */
.dsf-dialog-content::-webkit-scrollbar {
  width: 8px;
}

.dsf-dialog-content::-webkit-scrollbar-track {
  background: transparent;
}

.dsf-dialog-content::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 204, 0.2);
  border-radius: 4px;
}

.dsf-dialog-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 255, 204, 0.4);
}
```

## Step 4: Test Static Rendering (5 minutes)

Add to your `app.tsx` temporarily to test:

```typescript
import { DSFDialog } from './components/radix/Dialog';

// Inside your App component, add:
<DSFDialog
  trigger={
    <button className="action-button action-button-primary">
      Open Test Dialog
    </button>
  }
  title="Test Dialog"
  description="This is a test of the Radix Dialog component with DSF styling"
>
  <div style={{ padding: '20px 0' }}>
    <p style={{ color: 'var(--text-primary)', marginBottom: '16px' }}>
      This dialog is:
    </p>
    <ul style={{ color: 'var(--text-secondary)', paddingLeft: '20px' }}>
      <li>Styled with your neon cyberpunk aesthetic ✨</li>
      <li>Accessible (keyboard nav, ARIA, focus trap) ♿</li>
      <li>Animated (smooth open/close) 🎬</li>
      <li>Agent-controllable (coming next!) 🤖</li>
    </ul>
  </div>
</DSFDialog>
```

Run canvas server:
```bash
bun run canvas
```

Visit `http://localhost:3030` and click the button. You should see a beautiful neon-styled modal!

## Step 5: Make It Agent-Controllable (8 minutes)

### 5.1: Update canvas_ui Tool

In `src/tools/impl/canvas_ui.ts`, update the validator to recognize Dialog:

```typescript
const VALID_TYPES = new Set([
  // ... existing types
  "Dialog",
  "Tabs",
  "Slider",
  "Switch"
]);
```

### 5.2: Update DynamicRenderer

Create or update `src/canvas/components/DynamicRenderer.tsx`:

```typescript
import { DSFDialog } from './radix/Dialog';
// ... other imports

export function DynamicRenderer({ spec, onInteraction }: RendererProps) {
  const { type, id, props, children } = spec;

  switch (type) {
    case 'Dialog':
      return (
        <DSFDialog
          trigger={
            props.trigger ?
              <DynamicRenderer spec={props.trigger} onInteraction={onInteraction} /> :
              undefined
          }
          title={props.title}
          description={props.description}
          open={props.open}
          onOpenChange={(open) => {
            if (id && props.onOpenChange) {
              onInteraction(id, 'dialog_change', { open });
            }
          }}
        >
          {children ? (
            Array.isArray(children) ? (
              children.map((child, i) => (
                <DynamicRenderer key={i} spec={child} onInteraction={onInteraction} />
              ))
            ) : (
              <DynamicRenderer spec={children} onInteraction={onInteraction} />
            )
          ) : null}
        </DSFDialog>
      );

    // ... other cases
  }
}
```

### 5.3: Update Canvas App

In `src/canvas/app.tsx`, integrate DynamicRenderer:

```typescript
import { DynamicRenderer } from './components/DynamicRenderer';

// In your component:
const [dynamicUI, setDynamicUI] = useState<ComponentSpec | null>(null);

// Handle Agent Bus events
busClient.on("agent.canvas_update", (event) => {
  if (event.payload.operation === "render") {
    setDynamicUI(event.payload.definition);
  }
});

// In render:
{dynamicUI && (
  <DynamicRenderer
    spec={dynamicUI}
    onInteraction={handleInteraction}
  />
)}
```

## Step 6: Test Agent Control (5 minutes)

In your CLI, ask the agent:

```
You: Create a dialog that shows a story preview

Agent: [Uses canvas_ui tool]
canvas_ui({
  operation: "render",
  component_id: "story-preview-dialog",
  definition: {
    type: "Dialog",
    id: "story-dialog",
    props: {
      title: "Story Preview",
      description: "A glimpse into the Neon Underground",
      trigger: {
        type: "Button",
        props: {
          label: "Preview Story",
          variant: "primary"
        }
      }
    },
    children: [
      {
        type: "Markdown",
        props: {
          content: "The city breathed through ventilation shafts..."
        }
      }
    ]
  }
})
```

Canvas should display a button that opens a styled dialog! 🎉

## Troubleshooting

**Dialog doesn't appear:**
- Check browser console for errors
- Verify Radix packages installed: `bun pm ls | grep radix`
- Check z-index: Dialog overlay should be 1000+

**Styling looks wrong:**
- Verify CSS variables are defined (check your existing styles.css)
- Check class names match (dsf-dialog-* classes)
- Inspect element to see if styles are applied

**Agent can't render it:**
- Check DynamicRenderer includes "Dialog" case
- Verify canvas_ui tool validator includes "Dialog"
- Check Agent Bus events in Network tab (WebSocket messages)

## Next Components to Add

Once Dialog works, add these in order:

1. **Tabs** - Story navigation, multi-panel views
2. **Slider** - Interactive parameters, timelines
3. **Switch** - Toggle features, dark mode
4. **Select** - Dropdown menus, filters

Each follows the same pattern:
1. Install Radix package
2. Create styled wrapper component
3. Add CSS matching your aesthetic
4. Add to DynamicRenderer
5. Test with agent

## Success Checklist

- [ ] Radix Dialog package installed
- [ ] DSFDialog component created
- [ ] Dialog styles added to styles.css
- [ ] Static rendering works (manual test)
- [ ] DynamicRenderer includes Dialog case
- [ ] Agent can render dialog via canvas_ui
- [ ] Dialog animations smooth
- [ ] Keyboard navigation works (Esc to close)
- [ ] Styling matches your neon aesthetic

**Time to complete:** ~30 minutes
**Difficulty:** Medium
**Result:** First agent-composable Radix component! 🚀

## What You've Achieved

You now have:
- ✅ Radix UI integrated with your styling
- ✅ Agent can create interactive modals
- ✅ Accessibility handled automatically
- ✅ Pattern for adding more components

**Next:** Add Tabs, Slider, and Switch following the same pattern. See `component-strategy.md` for full roadmap.

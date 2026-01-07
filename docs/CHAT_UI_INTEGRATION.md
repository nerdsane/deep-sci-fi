# Chat UI Integration into Canvas

**Goal:** Integrate conversational agent chat into the existing Canvas UI while preserving the "immersive and magical" design aesthetic.

**Approach:** Extend the existing FloatingInput (Cmd+K) system into a persistent, context-aware chat panel.

---

## 🎨 Design Principles

1. **Non-intrusive** - Canvas remains the focus, chat is supportive
2. **Context-aware** - Chat knows what you're viewing (world, story, element)
3. **Responsive** - Adapts to laptop and mobile screens
4. **Immersive** - Matches existing neon/cyberpunk aesthetic
5. **Accessible** - Keyboard shortcuts, ARIA labels

---

## 💻 Desktop Layout (≥ 1024px)

```
┌────────────────────────────────────────────────────────────────┐
│  Deep Sci-Fi                                    [User] [⚙]      │
├──────┬─────────────────────────────────────────────┬───────────┤
│      │                                             │           │
│ 🌍   │  ╔═══════════════════════════════════════╗ │ 💬 Chat   │
│ Worlds│  ║                                       ║ │           │
│      │  ║         WORLD EXPLORER                ║ │ Agent:    │
│ › DC │  ║                                       ║ │ Welcome!  │
│ › SOL│  ║  [Elements Grid]                      ║ │ I'm the   │
│      │  ║                                       ║ │ world     │
│ + New│  ║  [Rules Panel]                        ║ │ agent for │
│      │  ║                                       ║ │ Dystopian │
│──────┤  ║                                       ║ │ City.     │
│ 📖   │  ║  [Constraints]                        ║ │           │
│Stories│  ║                                       ║ │ What      │
│      │  ║                                       ║ │ would you │
│ › UPS│  ╚═══════════════════════════════════════╝ │ like to   │
│ › FALL                                           │ create?   │
│      │  Context: Dystopian City • World View    │           │
│ + New│                                            │ You:      │
│      │                                            │ ┌─────────┤
│      │                                            │ │Add a    │
│      │                                            │ │new...   │
│      │                                            │ └─────────┤
│      │                                            │  [Send]   │
│      │                                            │           │
│      │                                            │ [≡] ━━━   │
│      │                                            │ Agent     │
│      │                                            │ thinking...
└──────┴────────────────────────────────────────────┴───────────┘

Layout:
├── Sidebar (240px) - Worlds/Stories list
├── Main Canvas (flex-1) - World/Story content
└── Chat Panel (320px) - Agent conversation
```

### Key Features (Desktop)

1. **Persistent Chat Panel**
   - Always visible on right side
   - Collapsible via `[≡]` button
   - Auto-scrolls to latest message
   - Shows agent status (thinking, ready)

2. **Context Bar**
   - Shows current context: "Dystopian City • World View"
   - Updates when switching between world/story
   - Click to change context

3. **Message Types**
   - Agent messages (left-aligned, neon cyan)
   - User messages (right-aligned, purple)
   - System messages (centered, gray)
   - Agent actions (inline cards: "Created element: Marcus Kane")

4. **Quick Actions**
   - Floating buttons above input:
     - "✨ Generate Image"
     - "🧪 Check Consistency"
     - "📊 Assess Quality"

---

## 📱 Mobile Layout (< 1024px)

```
┌──────────────────────────┐
│  Deep Sci-Fi      [☰] [U]│
├──────────────────────────┤
│                          │
│  ╔══════════════════════╗│
│  ║                      ║│
│  ║   WORLD EXPLORER     ║│
│  ║                      ║│
│  ║  [Elements Grid]     ║│
│  ║                      ║│
│  ║  [Rules Panel]       ║│
│  ║                      ║│
│  ╚══════════════════════╝│
│                          │
│ Context: Dystopian City  │
│                          │
│ [Swipe up to chat]       │
│                          │
└──────────────────────────┘
         ▲ Swipe up
         │
┌──────────────────────────┐
│  💬 Chat                 │
│  ──────────────────      │
│                          │
│ Agent:                   │
│ What would you like to   │
│ create today?            │
│                          │
│ You:                     │
│ Add a new character...   │
│                          │
│ ┌────────────────────┐   │
│ │ Your message...    │   │
│ └────────────────────┘   │
│              [Send ↗]    │
│                          │
│ [━━━━━ Swipe down ━━━━━] │
└──────────────────────────┘
```

### Key Features (Mobile)

1. **Bottom Drawer**
   - Swipe up to reveal chat
   - Swipe down to dismiss
   - Persistent "floating bubble" when minimized
   - Shows unread message count

2. **Full-Screen Chat Mode**
   - Double-tap chat bubble → full-screen chat
   - Canvas hidden, focus on conversation
   - Back button returns to canvas

3. **Compact Context**
   - Sticky header shows: "DC • World"
   - Tap to switch context

4. **Gesture Controls**
   - Swipe up: Open chat
   - Swipe down: Close chat
   - Long-press message: Copy text
   - Swipe message left: Quick actions

---

## 🧩 Component Structure

### ChatPanel Component

```tsx
// apps/web/components/chat/ChatPanel.tsx

interface ChatPanelProps {
  worldId?: string;
  storyId?: string;
  onSendMessage: (message: string, context: ChatContext) => Promise<void>;
  messages: Message[];
  agentStatus: 'idle' | 'thinking' | 'error';
  isMobile: boolean;
}

export function ChatPanel({
  worldId,
  storyId,
  onSendMessage,
  messages,
  agentStatus,
  isMobile
}: ChatPanelProps) {
  const [isOpen, setIsOpen] = useState(!isMobile);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Determine context
  const context: ChatContext = {
    type: storyId ? 'story' : 'world',
    worldId,
    storyId,
    view: 'canvas'
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    await onSendMessage(input, context);
    setInput('');
  };

  if (isMobile) {
    return (
      <ChatDrawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        messages={messages}
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
        agentStatus={agentStatus}
        context={context}
      />
    );
  }

  return (
    <aside className="chat-panel">
      <ChatHeader context={context} onCollapse={() => setIsOpen(false)} />
      <MessageList messages={messages} agentStatus={agentStatus} />
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={agentStatus === 'thinking'}
      />
    </aside>
  );
}
```

### Message Component

```tsx
// apps/web/components/chat/Message.tsx

interface MessageProps {
  message: Message;
}

export function Message({ message }: MessageProps) {
  const isAgent = message.role === 'agent';

  return (
    <div className={`message ${isAgent ? 'message--agent' : 'message--user'}`}>
      {isAgent && (
        <div className="message__avatar">
          <AgentIcon />
        </div>
      )}

      <div className="message__content">
        {message.type === 'text' && (
          <MessageText content={message.content} />
        )}

        {message.type === 'action' && (
          <MessageAction action={message.action} data={message.data} />
        )}

        {message.type === 'system' && (
          <MessageSystem content={message.content} />
        )}

        <span className="message__timestamp">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {!isAgent && (
        <div className="message__avatar">
          <UserAvatar />
        </div>
      )}
    </div>
  );
}
```

### Message Action (Agent Actions)

```tsx
// apps/web/components/chat/MessageAction.tsx

interface MessageActionProps {
  action: 'created_element' | 'updated_world' | 'generated_image' | 'checked_consistency';
  data: any;
}

export function MessageAction({ action, data }: MessageActionProps) {
  switch (action) {
    case 'created_element':
      return (
        <div className="message-action message-action--created">
          <div className="message-action__icon">✨</div>
          <div className="message-action__body">
            <strong>Created Element</strong>
            <p>{data.elementType}: {data.elementName}</p>
            <button
              className="message-action__button"
              onClick={() => openElement(data.elementId)}
            >
              View →
            </button>
          </div>
        </div>
      );

    case 'generated_image':
      return (
        <div className="message-action message-action--image">
          <div className="message-action__icon">🎨</div>
          <div className="message-action__body">
            <strong>Generated Image</strong>
            <img
              src={data.imageUrl}
              alt={data.description}
              className="message-action__image"
              loading="lazy"
            />
            <p className="message-action__prompt">{data.prompt}</p>
          </div>
        </div>
      );

    case 'checked_consistency':
      return (
        <div className="message-action message-action--check">
          <div className="message-action__icon">
            {data.consistent ? '✅' : '⚠️'}
          </div>
          <div className="message-action__body">
            <strong>Consistency Check</strong>
            <p>
              {data.consistent
                ? 'No contradictions found'
                : `Found ${data.contradictions.length} issues`
              }
            </p>
            {!data.consistent && (
              <ul className="message-action__list">
                {data.contradictions.map((c: any) => (
                  <li key={c.id}>{c.description}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      );

    default:
      return null;
  }
}
```

---

## 🎨 Styling (Preserve Existing Aesthetic)

```css
/* apps/web/styles/chat.css */

/* Preserve existing color scheme */
:root {
  --cyan: #00ffcc;           /* Main brand cyan */
  --cyan-bright: #00ffff;    /* Bright cyan */
  --purple: #aa00ff;         /* Accent purple */
  --dark-bg: #0a0a0f;        /* Dark background */
  --dark-surface: #12121a;   /* Surface background */
  --text-primary: #e0e0e0;   /* Primary text */
  --text-secondary: #8080a0; /* Secondary text */
}

/* Chat Panel */
.chat-panel {
  width: 320px;
  height: 100vh;
  background: var(--dark-surface);
  border-left: 1px solid rgba(0, 255, 204, 0.2);
  display: flex;
  flex-direction: column;

  /* Glassmorphism effect */
  backdrop-filter: blur(10px);
  background: linear-gradient(
    180deg,
    rgba(18, 18, 26, 0.9) 0%,
    rgba(10, 10, 15, 0.95) 100%
  );
}

/* Message List */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;

  /* Custom scrollbar (neon cyan) */
  scrollbar-width: thin;
  scrollbar-color: var(--cyan) transparent;
}

/* Message (Agent) */
.message--agent {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.message--agent .message__content {
  background: rgba(0, 255, 204, 0.1);
  border: 1px solid rgba(0, 255, 204, 0.3);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  max-width: 85%;

  /* Neon glow effect */
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.1);
}

/* Message (User) */
.message--user {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  flex-direction: row-reverse;
}

.message--user .message__content {
  background: rgba(170, 0, 255, 0.15);
  border: 1px solid rgba(170, 0, 255, 0.4);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  max-width: 85%;
  text-align: right;

  /* Purple glow */
  box-shadow: 0 0 20px rgba(170, 0, 255, 0.15);
}

/* Chat Input */
.chat-input {
  padding: 1rem;
  border-top: 1px solid rgba(0, 255, 204, 0.2);
  background: rgba(10, 10, 15, 0.8);
}

.chat-input__form {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.chat-input__field {
  flex: 1;
  background: rgba(0, 255, 204, 0.05);
  border: 1px solid rgba(0, 255, 204, 0.3);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  color: var(--text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;

  transition: all 0.2s ease;
}

.chat-input__field:focus {
  outline: none;
  border-color: var(--cyan);
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.2);
}

.chat-input__send {
  background: var(--cyan);
  color: var(--dark-bg);
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  /* Neon glow */
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.4);
}

.chat-input__send:hover {
  background: var(--cyan-bright);
  box-shadow: 0 0 30px rgba(0, 255, 204, 0.6);
  transform: translateY(-2px);
}

.chat-input__send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Message Action Card */
.message-action {
  display: flex;
  gap: 0.75rem;
  background: rgba(0, 255, 204, 0.05);
  border: 1px solid rgba(0, 255, 204, 0.2);
  border-radius: 8px;
  padding: 1rem;
  margin-top: 0.5rem;

  animation: slideInFromLeft 0.3s ease-out;
}

@keyframes slideInFromLeft {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.message-action__icon {
  font-size: 1.5rem;
}

.message-action__body {
  flex: 1;
}

.message-action__button {
  background: rgba(0, 255, 204, 0.2);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 0.5rem;
}

.message-action__button:hover {
  background: rgba(0, 255, 204, 0.3);
  box-shadow: 0 0 15px rgba(0, 255, 204, 0.3);
}

/* Agent Thinking Indicator */
.agent-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(0, 255, 204, 0.05);
  border-radius: 8px;
  margin: 0.5rem 1rem;
}

.agent-status__dots {
  display: flex;
  gap: 0.25rem;
}

.agent-status__dot {
  width: 8px;
  height: 8px;
  background: var(--cyan);
  border-radius: 50%;
  animation: pulse 1.4s infinite ease-in-out;
}

.agent-status__dot:nth-child(2) {
  animation-delay: 0.2s;
}

.agent-status__dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes pulse {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Mobile Drawer */
@media (max-width: 1023px) {
  .chat-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    height: 70vh;
    transform: translateY(100%);
    transition: transform 0.3s ease-out;
    border-left: none;
    border-top: 1px solid rgba(0, 255, 204, 0.2);
    border-radius: 16px 16px 0 0;
    z-index: 1000;
  }

  .chat-panel--open {
    transform: translateY(0);
  }

  .chat-panel__handle {
    width: 40px;
    height: 4px;
    background: rgba(255, 255, 255, 0.3);
    border-radius: 2px;
    margin: 0.5rem auto;
    cursor: grab;
  }
}

/* Floating Chat Bubble (Mobile) */
.chat-bubble {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  width: 56px;
  height: 56px;
  background: var(--cyan);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(0, 255, 204, 0.5);
  z-index: 999;
  transition: all 0.2s ease;
}

.chat-bubble:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 30px rgba(0, 255, 204, 0.7);
}

.chat-bubble__icon {
  color: var(--dark-bg);
  font-size: 1.5rem;
}

.chat-bubble__badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--purple);
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}
```

---

## ⚡ Features

### Context-Aware Input

```tsx
// Detect current context and show in chat
const ChatContextBar = ({ worldId, storyId, elementId }: ChatContextBarProps) => {
  const context = useMemo(() => {
    if (elementId) return `Element: ${getElementName(elementId)}`;
    if (storyId) return `Story: ${getStoryTitle(storyId)}`;
    if (worldId) return `World: ${getWorldName(worldId)}`;
    return 'Canvas';
  }, [worldId, storyId, elementId]);

  return (
    <div className="chat-context-bar">
      <span className="chat-context-bar__icon">◈</span>
      <span className="chat-context-bar__text">{context}</span>
      <button className="chat-context-bar__change">Change</button>
    </div>
  );
};
```

### Quick Actions

```tsx
// Quick action buttons above input
const QuickActions = ({ onAction }: QuickActionsProps) => (
  <div className="quick-actions">
    <button
      className="quick-action"
      onClick={() => onAction('generate-image')}
      title="Generate image"
    >
      ✨ Image
    </button>
    <button
      className="quick-action"
      onClick={() => onAction('check-consistency')}
      title="Check consistency"
    >
      🧪 Check
    </button>
    <button
      className="quick-action"
      onClick={() => onAction('assess-quality')}
      title="Assess quality"
    >
      📊 Quality
    </button>
  </div>
);
```

### Keyboard Shortcuts

```tsx
// Global keyboard shortcuts
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Cmd+K or Ctrl+K: Focus chat input
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      chatInputRef.current?.focus();
    }

    // Esc: Blur chat input
    if (e.key === 'Escape' && document.activeElement === chatInputRef.current) {
      chatInputRef.current?.blur();
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

---

## 📱 Mobile Gestures

```tsx
// Swipe gesture for mobile drawer
const useChatDrawerGesture = () => {
  const [startY, setStartY] = useState(0);
  const [currentY, setCurrentY] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  const handleTouchStart = (e: TouchEvent) => {
    setStartY(e.touches[0].clientY);
  };

  const handleTouchMove = (e: TouchEvent) => {
    setCurrentY(e.touches[0].clientY);
  };

  const handleTouchEnd = () => {
    const deltaY = currentY - startY;

    // Swipe up to open
    if (deltaY < -50 && !isOpen) {
      setIsOpen(true);
    }

    // Swipe down to close
    if (deltaY > 50 && isOpen) {
      setIsOpen(false);
    }

    setStartY(0);
    setCurrentY(0);
  };

  return { isOpen, handleTouchStart, handleTouchMove, handleTouchEnd };
};
```

---

## ✅ Summary

**Chat Integration Strategy:**

1. **Desktop:** Persistent side panel (320px wide)
2. **Mobile:** Bottom drawer + floating bubble
3. **Context-aware:** Shows current world/story/element
4. **Message types:** Text, action cards, system messages
5. **Styling:** Preserves existing neon/cyberpunk aesthetic
6. **Keyboard shortcuts:** Cmd+K to focus, Esc to blur
7. **Gestures:** Swipe up/down on mobile

**Migration Plan:**

1. Extract FloatingInput logic
2. Create ChatPanel component
3. Add MessageList, Message, MessageAction components
4. Style with existing color scheme
5. Add responsive behavior (drawer on mobile)
6. Integrate with tRPC API for agent chat

**Result:** Seamless chat experience that feels native to the Canvas while maintaining the immersive design.

---

**Next:** See [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) for full implementation timeline.

'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import type { World, Story } from '@/types/dsf';
import type { ComponentSpec } from '@/components/canvas/types';
import { DynamicRenderer } from '@/components/canvas/DynamicRenderer';
import { MountPoint } from '@/components/canvas/MountPoint';
import { ImmersiveStoryReader } from '@/components/canvas/story';
import { WorldSpace } from '@/components/canvas/world';
import { WelcomeSpace } from '@/components/canvas/welcome';
import { FeedbackProvider, useFeedbackSafe } from '@/components/canvas/context/FeedbackContext';
import { ToastContainer, AgentStatus } from '@/components/canvas/feedback';
import { FloatingInput, useFloatingInput, InteractiveElement, type ElementType } from '@/components/canvas/interaction';
import { AgentSuggestions, type AgentSuggestion, type Suggestion } from '@/components/canvas/agent';
import { ChatSidebar } from '@/components/chat/ChatSidebar';

// ============================================================================
// Types
// ============================================================================

type View = 'canvas' | 'world' | 'story';

interface AgentUIEntry {
  componentId: string;
  spec: ComponentSpec;
  mode: 'overlay' | 'fullscreen' | 'inline';
}

interface AppState {
  view: View;
  worlds: World[];
  stories: Story[];
  selectedWorld: World | null;
  selectedStory: Story | null;
  loading: boolean;
  error: string | null;
  agentUI: Map<string, AgentUIEntry>;
  fullscreenUI: AgentUIEntry | null;
  agentThinking: boolean;
  agentAction?: string;
  useImmersiveWorld: boolean;
  pendingExperience: { storyId: string; spec: any } | null;
  agentSuggestions: AgentSuggestion[];
}

// ============================================================================
// Main App Component
// ============================================================================

function App() {
  const [state, setState] = useState<AppState>({
    view: 'canvas',
    worlds: [],
    stories: [],
    selectedWorld: null,
    selectedStory: null,
    loading: true,
    error: null,
    agentUI: new Map(),
    fullscreenUI: null,
    agentThinking: false,
    useImmersiveWorld: true,
    pendingExperience: null,
    agentSuggestions: [],
  });

  const feedback = useFeedbackSafe();

  // ESC key handler for fullscreen modes
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (state.fullscreenUI) {
          setState(s => ({ ...s, fullscreenUI: null }));
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.fullscreenUI]);

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setState((s) => ({ ...s, loading: true, error: null }));

      const [worldsRes, storiesRes] = await Promise.all([
        fetch('/api/worlds'),
        fetch('/api/stories'),
      ]);

      const worlds = await worldsRes.json() as World[];
      const stories = await storiesRes.json() as Story[];

      setState((s) => ({
        ...s,
        worlds,
        stories,
        loading: false,
      }));
    } catch (error) {
      setState((s) => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load data',
        loading: false,
      }));
    }
  }

  function selectWorld(world: World) {
    setState((s) => ({
      ...s,
      view: 'world',
      selectedWorld: world,
    }));
  }

  function selectStory(story: Story) {
    setState((s) => ({
      ...s,
      view: 'story',
      selectedStory: story,
    }));
  }

  function goBack() {
    if (state.view === 'story') {
      setState((s) => ({ ...s, view: 'world', pendingExperience: null, agentThinking: false }));
    } else if (state.view === 'world') {
      setState((s) => ({ ...s, view: 'canvas', selectedWorld: null }));
    }
  }

  function goHome() {
    setState((s) => ({
      ...s,
      view: 'canvas',
      selectedWorld: null,
      selectedStory: null,
      pendingExperience: null,
      agentThinking: false,
    }));
  }

  function handleDynamicUIInteraction(
    componentId: string,
    interactionType: string,
    data: any,
    target?: string
  ) {
    console.log('[Dynamic UI] Interaction:', { componentId, interactionType, data, target });
  }

  function handleElementAction(actionId: string, elementId: string, elementType: ElementType, elementData?: any) {
    console.log('[Canvas] Element action:', { actionId, elementId, elementType });
    feedback?.showToast(`Action: ${actionId}`, 'agent');
    setState(s => ({ ...s, agentThinking: true, agentAction: `Processing ${actionId}...` }));
  }

  function handleSuggestionAccept(suggestion: Suggestion) {
    console.log('[Canvas] Suggestion accepted:', suggestion);
    feedback?.showToast(`Working on: ${suggestion.title}`, 'agent');
    setState(s => ({ ...s, agentThinking: true, agentAction: suggestion.action }));
  }

  function handleSuggestionDismiss(suggestionId: string) {
    console.log('[Canvas] Suggestion dismissed:', suggestionId);
  }

  // Handle messages from chat
  function handleChatMessage(message: string) {
    console.log('[Chat] Message sent:', message);
    setState(s => ({ ...s, agentThinking: true, agentAction: 'Processing...' }));
    // This will be connected to the Letta agent API
  }

  if (state.loading) {
    return (
      <div className="app-layout">
        <ChatSidebar onSendMessage={handleChatMessage} />
        <div className="canvas-container">
          <LoadingScreen />
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="app-layout">
        <ChatSidebar onSendMessage={handleChatMessage} />
        <div className="canvas-container">
          <ErrorScreen error={state.error} onRetry={loadData} />
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <ChatSidebar onSendMessage={handleChatMessage} />

      <div className="canvas-container">
        <div className="app">
          <Header
            view={state.view}
            selectedWorld={state.selectedWorld}
            selectedStory={state.selectedStory}
            onBack={goBack}
            onHome={goHome}
          />

          {/* Agent status indicator */}
          <AgentStatus
            isThinking={state.agentThinking}
            action={state.agentAction}
          />

          <main className="main-content">
            {state.view === 'canvas' && (
              <WelcomeSpace
                worlds={state.worlds}
                stories={state.stories}
                onSelectWorld={selectWorld}
                onSelectStory={selectStory}
                onElementAction={handleElementAction}
              />
            )}

            {state.view === 'world' && state.selectedWorld && (
              <WorldSpace
                world={state.selectedWorld}
                stories={state.stories.filter(
                  (s) => s.world_checkpoint === getWorldCheckpointName(state.selectedWorld!)
                )}
                onSelectStory={selectStory}
                onStartNewStory={() => {
                  const checkpoint = getWorldCheckpointName(state.selectedWorld!);
                  fetch(`/api/world/${checkpoint}/new-story`, { method: 'POST' })
                    .then(() => loadData())
                    .catch(console.error);
                }}
                onElementAction={handleElementAction}
              />
            )}

            {state.view === 'story' && state.selectedStory && (
              <StoryView
                story={state.selectedStory}
                agentUI={state.agentUI}
                onInteraction={handleDynamicUIInteraction}
                onElementAction={handleElementAction}
              />
            )}
          </main>

          {/* Agent Suggestions */}
          <AgentSuggestions
            world={state.selectedWorld}
            story={state.selectedStory}
            stories={state.stories}
            agentSuggestions={state.agentSuggestions}
            onAccept={handleSuggestionAccept}
            onDismiss={handleSuggestionDismiss}
            position="floating"
          />

          {/* Global toast notifications */}
          <ToastContainer />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Header Component
// ============================================================================

function Header({
  view,
  selectedWorld,
  selectedStory,
  onBack,
  onHome,
}: {
  view: View;
  selectedWorld: World | null;
  selectedStory: Story | null;
  onBack: () => void;
  onHome: () => void;
}) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo" onClick={onHome}>
          <pre className="logo-ascii">
{`██████╗ ███████╗███████╗██████╗
██╔══██╗██╔════╝██╔════╝██╔══██╗
██║  ██║█████╗  █████╗  ██████╔╝
██║  ██║██╔══╝  ██╔══╝  ██╔═══╝
██████╔╝███████╗███████╗██║
╚═════╝ ╚══════╝╚══════╝╚═╝
███████╗ ██████╗██╗      ███████╗██╗
██╔════╝██╔════╝██║      ██╔════╝██║
███████╗██║     ██║█████╗█████╗  ██║
╚════██║██║     ██║╚════╝██╔══╝  ██║
███████║╚██████╗██║      ██║     ██║
╚══════╝ ╚═════╝╚═╝      ╚═╝     ╚═╝`}
          </pre>
        </div>
        {view !== 'canvas' && (
          <button className="back-button" onClick={onBack}>
            ← Back
          </button>
        )}
      </div>

      <nav className="breadcrumb">
        <span className="breadcrumb-item" onClick={onHome}>
          Canvas
        </span>
        {selectedWorld && (
          <>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-item">
              {getWorldTitle(selectedWorld)}
            </span>
          </>
        )}
        {selectedStory && (
          <>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-item">{selectedStory.metadata.title}</span>
          </>
        )}
      </nav>
    </header>
  );
}

// ============================================================================
// Story View (simplified)
// ============================================================================

function StoryView({
  story,
  agentUI,
  onInteraction,
  onElementAction,
}: {
  story: Story;
  agentUI: Map<string, AgentUIEntry>;
  onInteraction: (componentId: string, interactionType: string, data: any, target?: string) => void;
  onElementAction?: (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => void;
}) {
  const segments = story.segments || [];
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(Math.max(0, segments.length - 1));
  const segment = segments[activeSegmentIndex];

  return (
    <div className="story-view">
      <div className="story-header">
        <div className="story-meta">
          <span className="story-status">{story.metadata.status}</span>
          <span className="story-segments">{segments.length} segments</span>
          <span className="story-world">
            World: {story.world_checkpoint} (v{story.world_version})
          </span>
        </div>
      </div>

      {segments.length === 0 ? (
        <div className="empty-state">No segments yet</div>
      ) : (
        <>
          <div className="segment-nav">
            {segments.map((seg, index) => (
              <button
                key={seg.id}
                className={`segment-nav-button ${index === activeSegmentIndex ? 'active' : ''}`}
                onClick={() => setActiveSegmentIndex(index)}
              >
                Segment {index + 1}
              </button>
            ))}
          </div>

          {segment && (
            <div className="segment-content">
              <div className="segment-header">
                <h3 className="segment-id">{segment.id}</h3>
                <span className="segment-word-count">{segment.word_count} words</span>
              </div>

              <div className="segment-text">
                {segment.content}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============================================================================
// Utility Components
// ============================================================================

function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-spinner"></div>
      <p>Loading Deep Sci-Fi...</p>
    </div>
  );
}

function ErrorScreen({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="error-screen">
      <h2>Error Loading Data</h2>
      <p>{error}</p>
      <button onClick={onRetry}>Retry</button>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function getWorldTitle(world: World): string {
  if (world.surface?.visible_elements && world.surface.visible_elements.length > 0 && world.surface.visible_elements[0]?.name) {
    return world.surface.visible_elements[0].name;
  }
  const premise = world.foundation?.core_premise || 'Untitled World';
  const words = premise.split(' ').slice(0, 5);
  return words.join(' ') + (words.length < premise.split(' ').length ? '...' : '');
}

function getWorldCheckpointName(world: World): string {
  if ((world as any).checkpoint_name) {
    return (world as any).checkpoint_name;
  }
  const premise = world.foundation?.core_premise || '';
  return premise
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .substring(0, 30) || 'unnamed_world';
}

// ============================================================================
// App with Providers
// ============================================================================

export default function Page() {
  return (
    <FeedbackProvider>
      <App />
    </FeedbackProvider>
  );
}

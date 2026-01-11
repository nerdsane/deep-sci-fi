'use client';

import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import dynamic from 'next/dynamic';
import type { World, Story } from '@/types/dsf';
import type { ComponentSpec } from '@/components/canvas/types';
import { DynamicRenderer } from '@/components/canvas/DynamicRenderer';
import { MountPoint } from '@/components/canvas/MountPoint';
import { ImmersiveStoryReader } from '@/components/canvas/story';
import { WorldSpace } from '@/components/canvas/world';
import { WelcomeSpace } from '@/components/canvas/welcome';

// Dynamic import for Observatory to avoid SSR issues with Three.js
const Observatory = dynamic(
  () => import('@/components/canvas/observatory/Observatory').then(mod => mod.Observatory),
  { ssr: false, loading: () => <div className="loading-screen"><div className="loading-spinner"></div><p>Loading 3D Observatory...</p></div> }
);
import { FeedbackProvider, useFeedbackSafe } from '@/components/canvas/context/FeedbackContext';
import { ToastContainer, AgentStatus } from '@/components/canvas/feedback';
import { FloatingInput, useFloatingInput, InteractiveElement, type ElementType } from '@/components/canvas/interaction';
import { AgentSuggestions, type AgentSuggestion, type Suggestion } from '@/components/canvas/agent';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { ShaderBackground } from '@/components/canvas/immersive';
import {
  getDefaultWSClient,
  UnifiedWSClient,
  type StreamChunk,
  type CanvasUIMessage,
  type SuggestionPayload,
  type ConnectedClient,
} from '@/lib/unified-ws-client';
import { ConfirmModal } from '@/components/ui';

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
  // WebSocket state
  wsConnected: boolean;
  cliConnected: boolean;
  // Agent type tracking
  agentType: 'user' | 'world' | null;
  agentWorldName: string | null;
  // Image generation tracking
  generatingWorldIds: Set<string>;
  // Delete modal state
  worldToDelete: World | null;
  isDeleting: boolean;
  // 3D Observatory mode
  useObservatory: boolean;
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
    wsConnected: false,
    cliConnected: false,
    agentType: null,
    agentWorldName: null,
    generatingWorldIds: new Set(),
    worldToDelete: null,
    isDeleting: false,
    useObservatory: true, // Default to 3D mode
  });

  const feedback = useFeedbackSafe();
  const feedbackRef = useRef(feedback);
  const wsClientRef = useRef<UnifiedWSClient | null>(null);

  // Keep feedbackRef current
  useEffect(() => {
    feedbackRef.current = feedback;
  }, [feedback]);

  // ============================================================================
  // WebSocket Connection
  // ============================================================================

  useEffect(() => {
    // Use singleton WebSocket client to avoid reconnection on StrictMode double-mount
    const wsClient = getDefaultWSClient();
    wsClientRef.current = wsClient;

    // Connection handlers
    wsClient.onConnect = (clientId, sessionId, clients) => {
      console.log('[App] WebSocket connected:', clientId);
      const hasCli = clients.some((c) => c.type === 'cli');
      setState((s) => ({ ...s, wsConnected: true, cliConnected: hasCli }));
      feedbackRef.current?.showToast('Connected to agent', 'success');
    };

    wsClient.onDisconnect = () => {
      console.log('[App] WebSocket disconnected');
      setState((s) => ({ ...s, wsConnected: false }));
    };

    wsClient.onError = (error) => {
      console.error('[App] WebSocket error:', error);
      feedbackRef.current?.showToast(`Connection error: ${error}`, 'warning');
    };

    // Client join/leave handlers
    wsClient.onClientJoined = (client) => {
      console.log('[App] Client joined:', client);
      if (client.type === 'cli') {
        setState((s) => ({ ...s, cliConnected: true }));
        feedbackRef.current?.showToast('CLI connected - chat sidebar hidden', 'info');
      }
    };

    wsClient.onClientLeft = (clientId, clientType) => {
      console.log('[App] Client left:', clientId, clientType);
      if (clientType === 'cli') {
        setState((s) => ({ ...s, cliConnected: false }));
        feedbackRef.current?.showToast('CLI disconnected', 'info');
      }
    };

    // State change handler
    wsClient.onStateChange = (event, data) => {
      console.log('[App] State change:', event, data);
      switch (event) {
        case 'agent_thinking':
          setState((s) => ({
            ...s,
            agentThinking: true,
            agentAction: 'Processing...',
          }));
          break;
        case 'agent_done':
          setState((s) => ({ ...s, agentThinking: false, agentAction: undefined }));
          break;
        case 'story_started':
        case 'story_continued':
          // Refresh data when story changes
          loadData();
          break;
        case 'world_entered':
          // Refresh data when world is created/saved/updated
          feedbackRef.current?.showToast('World updated', 'success');
          loadData();
          break;
        case 'image_generating':
          // Track that image is being generated for a world
          if (data?.worldId) {
            setState((s) => ({
              ...s,
              generatingWorldIds: new Set([...s.generatingWorldIds, data.worldId]),
            }));
          }
          break;
        case 'image_generated':
          // Update only the specific world with new asset - no full reload
          if (data?.worldId) {
            setState((s) => {
              const newSet = new Set(s.generatingWorldIds);
              newSet.delete(data.worldId);

              // Update the specific world's asset without reloading all worlds
              const updatedWorlds = s.worlds.map((world) => {
                if ((world as any).id === data.worldId && data.assetUrl) {
                  return {
                    ...world,
                    asset: {
                      id: data.assetId,
                      type: "image" as const,
                      path: data.assetUrl,
                      url: data.assetUrl,
                    },
                  };
                }
                return world;
              });

              return { ...s, generatingWorldIds: newSet, worlds: updatedWorlds };
            });
            feedbackRef.current?.showToast('Image generated', 'success');
          }
          break;
      }
    };

    // Canvas UI handler
    wsClient.onCanvasUI = (message) => {
      console.log('[App] Canvas UI:', message);
      handleCanvasUI(message);
    };

    // Suggestion handler
    wsClient.onSuggestion = (suggestion) => {
      console.log('[App] Suggestion:', suggestion);
      setState((s) => ({
        ...s,
        agentSuggestions: [
          ...s.agentSuggestions.filter((sug) => sug.id !== suggestion.id),
          {
            id: suggestion.id,
            title: suggestion.title,
            description: suggestion.description,
            priority: suggestion.priority,
            actionId: suggestion.actionId,
            actionLabel: suggestion.actionLabel,
            actionData: suggestion.actionData,
          },
        ].slice(-10), // Keep last 10
      }));
    };

    // Connect only if not already connected
    if (!wsClient.isConnected()) {
      wsClient.connect().catch((err) => {
        console.error('[App] Failed to connect:', err);
      });
    } else {
      // Already connected, update state
      setState((s) => ({ ...s, wsConnected: true }));
    }

    // Cleanup: Don't disconnect the singleton, just clear handlers
    // The WebSocket stays alive across React StrictMode remounts
    return () => {
      // Only clear handlers, don't disconnect the singleton
      wsClient.onConnect = null;
      wsClient.onDisconnect = null;
      wsClient.onError = null;
      wsClient.onClientJoined = null;
      wsClient.onClientLeft = null;
      wsClient.onStateChange = null;
      wsClient.onCanvasUI = null;
      wsClient.onSuggestion = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency - WebSocket should only connect once on mount

  // ============================================================================
  // Canvas UI Handling
  // ============================================================================

  function handleCanvasUI(message: CanvasUIMessage) {
    const { action, componentId, spec, mode } = message;

    setState((s) => {
      const newAgentUI = new Map(s.agentUI);

      switch (action) {
        case 'create':
        case 'update':
          if (spec) {
            if (mode === 'fullscreen') {
              return {
                ...s,
                fullscreenUI: { componentId, spec: spec as ComponentSpec, mode },
              };
            }
            newAgentUI.set(componentId, {
              componentId,
              spec: spec as ComponentSpec,
              mode: mode || 'overlay',
            });
          }
          break;
        case 'remove':
          newAgentUI.delete(componentId);
          if (s.fullscreenUI?.componentId === componentId) {
            return { ...s, fullscreenUI: null, agentUI: newAgentUI };
          }
          break;
      }

      return { ...s, agentUI: newAgentUI };
    });
  }

  // ============================================================================
  // Data Loading
  // ============================================================================

  async function loadData() {
    try {
      setState((s) => ({ ...s, loading: true, error: null }));

      const [worldsRes, storiesRes] = await Promise.all([
        fetch('/api/worlds'),
        fetch('/api/stories'),
      ]);

      const worlds = (await worldsRes.json()) as World[];
      const stories = (await storiesRes.json()) as Story[];

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

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  // ESC key handler for fullscreen modes
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (state.fullscreenUI) {
          setState((s) => ({ ...s, fullscreenUI: null }));
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.fullscreenUI]);

  // ============================================================================
  // Navigation (memoized to prevent canvas re-renders)
  // ============================================================================

  const selectWorld = useCallback((world: World) => {
    setState((s) => ({
      ...s,
      view: 'world',
      selectedWorld: world,
    }));
  }, []);

  const selectStory = useCallback((story: Story) => {
    setState((s) => ({
      ...s,
      view: 'story',
      selectedStory: story,
    }));
  }, []);

  const goBack = useCallback(() => {
    setState((s) => {
      if (s.view === 'story') {
        return {
          ...s,
          view: 'world' as View,
          pendingExperience: null,
          agentThinking: false,
        };
      } else if (s.view === 'world') {
        return { ...s, view: 'canvas' as View, selectedWorld: null };
      }
      return s;
    });
  }, []);

  const goHome = useCallback(() => {
    setState((s) => ({
      ...s,
      view: 'canvas',
      selectedWorld: null,
      selectedStory: null,
      pendingExperience: null,
      agentThinking: false,
    }));
  }, []);

  // ============================================================================
  // World Delete Handlers
  // ============================================================================

  const handleDeleteWorld = useCallback((world: World) => {
    setState((s) => ({ ...s, worldToDelete: world }));
  }, []);

  const cancelDeleteWorld = useCallback(() => {
    setState((s) => ({ ...s, worldToDelete: null, isDeleting: false }));
  }, []);

  const confirmDeleteWorld = useCallback(async () => {
    if (!state.worldToDelete) return;

    const worldId = (state.worldToDelete as any).id;
    const worldName = (state.worldToDelete as any).name || 'this world';

    setState((s) => ({ ...s, isDeleting: true }));

    try {
      const response = await fetch(`/api/worlds/${worldId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to delete world');
      }

      // Refresh data and close modal
      await loadData();
      setState((s) => ({ ...s, worldToDelete: null, isDeleting: false }));

      feedbackRef.current?.showToast(`"${worldName}" has been deleted`, 'success');
    } catch (error) {
      console.error('Failed to delete world:', error);
      feedbackRef.current?.showToast(
        error instanceof Error ? error.message : 'Failed to delete world',
        'warning'
      );
      setState((s) => ({ ...s, isDeleting: false }));
    }
  }, [state.worldToDelete]);

  // ============================================================================
  // Interaction Handlers (memoized to prevent canvas re-renders)
  // ============================================================================

  const handleDynamicUIInteraction = useCallback(
    (componentId: string, interactionType: string, data: any, target?: string) => {
      console.log('[Dynamic UI] Interaction:', { componentId, interactionType, data, target });
      wsClientRef.current?.sendInteraction(componentId, interactionType, data, target);
    },
    []
  );

  const handleElementAction = useCallback(
    (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => {
      console.log('[Canvas] Element action:', { actionId, elementId, elementType });
      feedbackRef.current?.showToast(`Action: ${actionId}`, 'agent');
      wsClientRef.current?.sendInteraction(elementId, 'element_action', {
        actionId,
        elementType,
        ...elementData,
      });
    },
    []
  );

  const handleSuggestionAccept = useCallback((suggestion: Suggestion) => {
    console.log('[Canvas] Suggestion accepted:', suggestion);
    feedbackRef.current?.showToast(`Working on: ${suggestion.title}`, 'agent');
    wsClientRef.current?.sendInteraction('suggestions', 'suggestion_accept', {
      suggestionId: suggestion.id || suggestion.title,
      action: suggestion.action,
    });
    setState((s) => ({
      ...s,
      agentSuggestions: s.agentSuggestions.filter(
        (sug) => sug.id !== suggestion.id && sug.title !== suggestion.title
      ),
    }));
  }, []);

  const handleSuggestionDismiss = useCallback((suggestionId: string) => {
    console.log('[Canvas] Suggestion dismissed:', suggestionId);
    setState((s) => ({
      ...s,
      agentSuggestions: s.agentSuggestions.filter((sug) => sug.id !== suggestionId),
    }));
  }, []);

  const handleAgentTypeChange = useCallback((agentType: 'user' | 'world', worldName?: string) => {
    console.log('[App] Agent type changed:', agentType, worldName);
    setState((s) => ({
      ...s,
      agentType,
      agentWorldName: worldName || null,
    }));
  }, []);

  // ============================================================================
  // Render
  // ============================================================================

  if (state.loading) {
    return (
      <div className="app-layout">
        {!state.cliConnected && (
          <ChatSidebar
            wsClient={wsClientRef.current}
            onAgentTypeChange={handleAgentTypeChange}
            agentType={state.agentType}
            agentWorldName={state.agentWorldName}
          />
        )}
        <div className="canvas-container">
          <ShaderBackground />
          <LoadingScreen />
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="app-layout">
        {!state.cliConnected && (
          <ChatSidebar
            wsClient={wsClientRef.current}
            onAgentTypeChange={handleAgentTypeChange}
            agentType={state.agentType}
            agentWorldName={state.agentWorldName}
          />
        )}
        <div className="canvas-container">
          <ShaderBackground />
          <ErrorScreen error={state.error} onRetry={loadData} />
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* Chat sidebar - hidden when CLI is connected */}
      {!state.cliConnected && (
        <ChatSidebar
            wsClient={wsClientRef.current}
            onAgentTypeChange={handleAgentTypeChange}
            agentType={state.agentType}
            agentWorldName={state.agentWorldName}
          />
      )}

      {/* CLI connected indicator */}
      {state.cliConnected && (
        <div className="cli-indicator">
          <span className="cli-dot" />
          <span>CLI Connected</span>
        </div>
      )}

      <div className="canvas-container">
        {/* Shader background - only behind canvas, not chat */}
        <ShaderBackground />
        <div className="app">
          <Header
            view={state.view}
            selectedWorld={state.selectedWorld}
            selectedStory={state.selectedStory}
            onBack={goBack}
            onHome={goHome}
            wsConnected={state.wsConnected}
          />

          {/* Agent status indicator */}
          <AgentStatus isThinking={state.agentThinking} action={state.agentAction} />

          <main className="main-content">
            {state.view === 'canvas' && (
              <>
                {/* Mode toggle */}
                <button
                  className="view-mode-toggle"
                  onClick={() => setState(s => ({ ...s, useObservatory: !s.useObservatory }))}
                  title={state.useObservatory ? 'Switch to classic view' : 'Switch to 3D observatory'}
                >
                  {state.useObservatory ? '◈ Classic' : '◇ 3D Observatory'}
                </button>

                {state.useObservatory ? (
                  <Observatory
                    worlds={state.worlds}
                    onSelectWorld={selectWorld}
                  />
                ) : (
                  <WelcomeSpace
                    worlds={state.worlds}
                    stories={state.stories}
                    onSelectWorld={selectWorld}
                    onSelectStory={selectStory}
                    onDeleteWorld={handleDeleteWorld}
                    onElementAction={handleElementAction}
                    generatingWorldIds={state.generatingWorldIds}
                  />
                )}
              </>
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

          {/* Overlay UI from agent */}
          {Array.from(state.agentUI.values())
            .filter((entry) => entry.mode === 'overlay')
            .map((entry) => (
              <div key={entry.componentId} className="agent-overlay-ui">
                <DynamicRenderer
                  spec={entry.spec}
                  onInteraction={(
                    _componentId: string,
                    interactionType: string,
                    data: any,
                    target?: string
                  ) => handleDynamicUIInteraction(entry.componentId, interactionType, data, target)}
                />
              </div>
            ))}

          {/* Fullscreen UI from agent */}
          {state.fullscreenUI && (
            <div className="agent-fullscreen-ui">
              <button
                className="fullscreen-close"
                onClick={() => setState((s) => ({ ...s, fullscreenUI: null }))}
              >
                ✕ Close
              </button>
              <DynamicRenderer
                spec={state.fullscreenUI.spec}
                onInteraction={(
                  _componentId: string,
                  interactionType: string,
                  data: any,
                  target?: string
                ) => handleDynamicUIInteraction(state.fullscreenUI!.componentId, interactionType, data, target)}
              />
            </div>
          )}

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

          {/* Delete World Confirmation Modal */}
          <ConfirmModal
            isOpen={!!state.worldToDelete}
            title="Delete World"
            message={`Are you sure you want to delete "${(state.worldToDelete as any)?.name || 'this world'}"?`}
            warning="This will permanently delete the world and all its stories, assets, and chat history. This action cannot be undone."
            confirmLabel="Delete World"
            cancelLabel="Cancel"
            variant="danger"
            onConfirm={confirmDeleteWorld}
            onCancel={cancelDeleteWorld}
            isLoading={state.isDeleting}
          />
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
  wsConnected,
}: {
  view: View;
  selectedWorld: World | null;
  selectedStory: Story | null;
  onBack: () => void;
  onHome: () => void;
  wsConnected: boolean;
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
        <span className={`ws-status ${wsConnected ? 'ws-connected' : 'ws-disconnected'}`} />
        <span className="breadcrumb-item" onClick={onHome}>
          Canvas
        </span>
        {selectedWorld && (
          <>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-item">{getWorldTitle(selectedWorld)}</span>
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
// Story View (simplified, memoized)
// ============================================================================

interface StoryViewProps {
  story: Story;
  agentUI: Map<string, AgentUIEntry>;
  onInteraction: (componentId: string, interactionType: string, data: any, target?: string) => void;
  onElementAction?: (
    actionId: string,
    elementId: string,
    elementType: ElementType,
    elementData?: any
  ) => void;
}

const StoryView = React.memo(function StoryView({
  story,
  agentUI,
  onInteraction,
  onElementAction,
}: StoryViewProps) {
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

              <div className="segment-text">{segment.content}</div>
            </div>
          )}
        </>
      )}
    </div>
  );
});

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
  if (
    world.surface?.visible_elements &&
    world.surface.visible_elements.length > 0 &&
    world.surface.visible_elements[0]?.name
  ) {
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
  return (
    premise
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_|_$/g, '')
      .substring(0, 30) || 'unnamed_world'
  );
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

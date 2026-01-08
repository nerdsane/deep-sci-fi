'use client';

import { useState } from 'react';
import { WelcomeSpace } from '@/components/canvas/welcome';
import { FeedbackProvider } from '@/components/canvas/context/FeedbackContext';
import { ToastContainer } from '@/components/canvas/feedback';
import type { World, Story } from '@/types/dsf';
import '@/app/canvas.css';
import '@/components/chat/chat-canvas.css';

// Mock chat components for demo
function DemoChatSidebar() {
  const [messages, setMessages] = useState([
    {
      id: '1',
      role: 'agent' as const,
      content: "Welcome! I can help you create new worlds, explore existing ones, or answer questions about your projects. What would you like to do?",
      timestamp: new Date(Date.now() - 300000),
    },
    {
      id: '2',
      role: 'user' as const,
      content: "Show me my worlds",
      timestamp: new Date(Date.now() - 120000),
    },
    {
      id: '3',
      role: 'agent' as const,
      content: "I found 3 worlds in your library. You have worlds about reality convergence, knowledge architecture, and distributed consciousness. Would you like to explore any of these?",
      timestamp: new Date(Date.now() - 60000),
    },
  ]);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }]);

    setInput('');

    // Simulate agent response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: "This is a demo - the chat will be fully functional once integrated with tRPC and the agent system.",
        timestamp: new Date(),
      }]);
    }, 1000);
  };

  return (
    <aside className="persistent-chat-sidebar">
      <div className="chat-header">
        <div className="chat-header-logo">
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
        <div className="chat-header-agent">
          <span className="agent-indicator"></span>
          <span>User Agent</span>
        </div>
      </div>

      <div className="message-list">
        {messages.map((message) => (
          <div key={message.id} className={`message message--${message.role}`}>
            {message.role === 'agent' && (
              <div className="message__avatar">
                <div className="avatar avatar--agent">◇</div>
              </div>
            )}

            <div className="message__content">
              <p className="message__text">{message.content}</p>
              <span className="message__timestamp">
                {formatTime(message.timestamp)}
              </span>
            </div>

            {message.role === 'user' && (
              <div className="message__avatar">
                <div className="avatar avatar--user">◈</div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="chat-input-container">
        <div className="chat-input">
          <form className="chat-input__form" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
            <textarea
              className="chat-input__field"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me to create a world, or select a world to work on..."
              rows={1}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <button
              type="submit"
              className="chat-input__send"
              disabled={!input.trim()}
            >
              Send ↗
            </button>
          </form>
          <div className="chat-input__hint">
            <kbd>⌘K</kbd> to focus · <kbd>Enter</kbd> to send
          </div>
        </div>
      </div>
    </aside>
  );
}

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (seconds < 60) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;

  return date.toLocaleDateString();
}

// Mock data for demo
const mockWorlds: World[] = [
  {
    development: {
      state: 'detailed',
      version: 3,
      created: '2025-01-01T00:00:00Z',
      last_modified: '2025-01-08T00:00:00Z',
    },
    surface: {
      visible_elements: [
        {
          id: 'char-001',
          type: 'character',
          name: 'The Convergence Station',
          description: 'A massive orbital platform where multiple reality streams intersect',
          detail_level: 'detailed',
          introduced_in_version: 1,
          last_modified_version: 2,
          properties: {},
        },
      ],
      revealed_in_story: {},
    },
    foundation: {
      core_premise: 'In a universe where reality branches at every decision, a coalition maintains convergence stations where all possibilities meet',
      deep_focus_areas: {
        primary: ['Reality mechanics', 'Divergence tracking'],
        depth_level: {},
      },
      rules: [
        {
          id: 'rule-001',
          statement: 'Each decision creates a new reality branch that can be observed but not altered',
          scope: 'universal',
          certainty: 'fundamental',
          introduced_in_version: 1,
        },
      ],
      history: {
        eras: ['Pre-Convergence', 'Station Era'],
      },
    },
    constraints: [],
  },
  {
    development: {
      state: 'draft',
      version: 2,
      created: '2025-01-05T00:00:00Z',
      last_modified: '2025-01-07T00:00:00Z',
    },
    surface: {
      visible_elements: [
        {
          id: 'loc-001',
          type: 'location',
          name: 'Neo-Alexandria',
          description: 'A city built vertically through cloud layers, each level representing a different era of human knowledge',
          detail_level: 'detailed',
          introduced_in_version: 1,
          last_modified_version: 2,
          properties: {},
        },
      ],
      revealed_in_story: {},
    },
    foundation: {
      core_premise: 'A post-scarcity civilization organizes itself around the preservation and expansion of knowledge, with cities serving as living libraries',
      deep_focus_areas: {
        primary: ['Knowledge architecture', 'Social organization'],
        depth_level: {},
      },
      rules: [
        {
          id: 'rule-002',
          statement: 'Information cannot be destroyed, only transformed',
          scope: 'universal',
          certainty: 'established',
          introduced_in_version: 1,
        },
      ],
    },
    constraints: [],
  },
  {
    development: {
      state: 'sketch',
      version: 1,
      created: '2025-01-08T00:00:00Z',
      last_modified: '2025-01-08T00:00:00Z',
    },
    surface: {
      visible_elements: [],
      revealed_in_story: {},
    },
    foundation: {
      core_premise: 'Consciousness can be distributed across vast distances through quantum entanglement, creating a civilization that thinks as one but experiences as many',
      deep_focus_areas: {
        primary: ['Distributed consciousness', 'Individual vs collective'],
        depth_level: {},
      },
      rules: [],
    },
    constraints: [],
  },
];

const mockStories: Story[] = [
  {
    id: 'story-001',
    world_checkpoint: 'world-001',
    world_version: 3,
    metadata: {
      title: 'The Observer Effect',
      created: '2025-01-02T00:00:00Z',
      last_updated: '2025-01-08T00:00:00Z',
      status: 'active',
      tags: ['mystery', 'reality-bending'],
    },
    segments: [
      {
        id: 'seg-001',
        content: 'Maya stood at the convergence point, watching infinite versions of herself make different choices...',
        word_count: 342,
        created: '2025-01-02T00:00:00Z',
        parent_segment: null,
        world_evolution: {},
      },
      {
        id: 'seg-002',
        content: 'The station trembled as another branch collapsed into the mainstream...',
        word_count: 284,
        created: '2025-01-04T00:00:00Z',
        parent_segment: 'seg-001',
        world_evolution: {},
      },
    ],
    endpoints: [],
    world_contributions: {
      characters_developed: [],
      locations_explored: [],
      rules_tested: [],
      new_rules_discovered: [],
      contradictions_found: [],
      themes_explored: ['identity', 'choice'],
    },
  },
  {
    id: 'story-002',
    world_checkpoint: 'world-002',
    world_version: 2,
    metadata: {
      title: 'The Last Librarian',
      created: '2025-01-06T00:00:00Z',
      last_updated: '2025-01-07T00:00:00Z',
      status: 'active',
      tags: ['post-scarcity', 'knowledge'],
    },
    segments: [
      {
        id: 'seg-003',
        content: 'In the highest tower of Neo-Alexandria, where ancient data streams met modern consciousness...',
        word_count: 421,
        created: '2025-01-06T00:00:00Z',
        parent_segment: null,
        world_evolution: {},
      },
    ],
    endpoints: [],
    world_contributions: {
      characters_developed: [],
      locations_explored: [],
      rules_tested: [],
      new_rules_discovered: [],
      contradictions_found: [],
      themes_explored: ['preservation', 'evolution'],
    },
  },
];

export default function DemoPage() {
  return (
    <FeedbackProvider>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '400px 1fr',
        height: '100vh',
        overflow: 'hidden',
        background: '#000'
      }}>
        <DemoChatSidebar />

        <div style={{
          overflowY: 'auto',
          overflowX: 'hidden',
          background: '#000'
        }}>
          <WelcomeSpace
            worlds={mockWorlds}
            stories={mockStories}
            onSelectWorld={(world) => {
              console.log('Selected world:', world);
              alert('World selection - will be integrated with routing');
            }}
            onSelectStory={(story) => {
              console.log('Selected story:', story);
              alert('Story selection - will be integrated with routing');
            }}
            onStartNewWorld={() => {
              console.log('Start new world');
              alert('Start new world - will be integrated with agent');
            }}
          />
        </div>

        <ToastContainer position="bottom-right" />
      </div>
    </FeedbackProvider>
  );
}

import React from 'react';
import type { World, Story } from '../../../types/dsf';
import { Hero, ScrollSection, ActionBar } from '../experience';
import { InteractiveElement, type ElementType } from '../interaction';
import './welcome-space.css';

export interface WelcomeSpaceProps {
  worlds: World[];
  stories: Story[];
  onSelectWorld: (world: World) => void;
  onSelectStory: (story: Story) => void;
  onStartNewWorld?: () => void;
  onElementAction?: (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => void;
}

// Helper to derive world title
function getWorldTitle(world: World): string {
  if (world.surface?.visible_elements?.[0]?.name) {
    return world.surface.visible_elements[0].name;
  }
  const premise = world.foundation?.core_premise || 'Untitled World';
  const words = premise.split(' ').slice(0, 5);
  return words.join(' ') + (words.length < premise.split(' ').length ? '...' : '');
}

// Helper to derive world era
function getWorldEra(world: World): string {
  return world.foundation?.history?.eras?.[0] || world.development?.state || 'Active';
}

// Helper to get world ID
function getWorldId(world: World): string {
  const premise = world.foundation?.core_premise || '';
  return premise.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 30) || 'world';
}

export function WelcomeSpace({
  worlds,
  stories,
  onSelectWorld,
  onSelectStory,
  onStartNewWorld,
  onElementAction,
}: WelcomeSpaceProps) {
  // Default action handler
  const handleAction = (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => {
    if (onElementAction) {
      onElementAction(actionId, elementId, elementType, elementData);
    } else if (actionId === 'enter' && elementType === 'world_card') {
      onSelectWorld(elementData);
    } else if (actionId === 'read' && elementType === 'story_card') {
      onSelectStory(elementData);
    }
  };
  // Get active stories for "Continue" section
  const activeStories = stories.filter(s => s.metadata.status === 'active');
  const recentStories = activeStories.slice(0, 3);

  // Get time-based greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  // Build welcome message
  const hasActiveStories = activeStories.length > 0;
  const subtitle = hasActiveStories
    ? `You have ${activeStories.length} stor${activeStories.length === 1 ? 'y' : 'ies'} in progress`
    : 'Ready to explore new worlds?';

  return (
    <div className="welcome-space">
      {/* Hero Section - Compact for content-first design */}
      <Hero
        title={greeting}
        subtitle={subtitle}
        meta={[
          `${worlds.length} worlds`,
          `${stories.length} stories`,
        ]}
        height="compact"
        overlay="gradient"
      />

      {/* Continue Reading Section */}
      {recentStories.length > 0 && (
        <section className="welcome-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="welcome-space__section-title">
              <span className="welcome-space__section-icon">→</span>
              Continue Reading
            </h2>
            <div className="welcome-space__stories">
              {recentStories.map((story, i) => (
                <ScrollSection key={story.id} animation="slide-left" delay={i * 100}>
                  <InteractiveElement
                    elementType="story_card"
                    elementId={story.id}
                    elementData={story}
                    onAction={handleAction}
                  >
                    <button
                      className="welcome-space__story-card"
                      onClick={() => onSelectStory(story)}
                    >
                      <div className="welcome-space__story-info">
                        <h3 className="welcome-space__story-title">{story.metadata.title}</h3>
                        <p className="welcome-space__story-meta">
                          {story.segments.length} segments · Last updated recently
                        </p>
                      </div>
                      <span className="welcome-space__story-arrow">→</span>
                    </button>
                  </InteractiveElement>
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Worlds Section */}
      {worlds.length > 0 && (
        <section className="welcome-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="welcome-space__section-title">
              <span className="welcome-space__section-icon">◈</span>
              Your Worlds
            </h2>
            <div className="welcome-space__worlds-grid">
              {worlds.map((world, i) => (
                <ScrollSection key={getWorldId(world) + i} animation="scale" delay={i * 100}>
                  <InteractiveElement
                    elementType="world_card"
                    elementId={getWorldId(world)}
                    elementData={world}
                    onAction={handleAction}
                  >
                    <button
                      className="welcome-space__world-card"
                      onClick={() => onSelectWorld(world)}
                    >
                      <div className="welcome-space__world-header">
                        <span className="welcome-space__world-badge">
                          {getWorldEra(world)}
                        </span>
                      </div>
                      <h3 className="welcome-space__world-name">{getWorldTitle(world)}</h3>
                      <p className="welcome-space__world-premise">{world.foundation?.core_premise || ''}</p>
                      <div className="welcome-space__world-stats">
                        <span>{world.surface?.visible_elements?.length || 0} elements</span>
                        <span>v{world.development?.version || 0}</span>
                      </div>
                    </button>
                  </InteractiveElement>
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Empty State */}
      {worlds.length === 0 && stories.length === 0 && (
        <section className="welcome-space__section welcome-space__section--empty">
          <ScrollSection animation="fade-up">
            <div className="welcome-space__empty">
              <span className="welcome-space__empty-icon">◇</span>
              <h3 className="welcome-space__empty-title">Begin Your Journey</h3>
              <p className="welcome-space__empty-text">
                Create your first world to start crafting stories.
              </p>
            </div>
          </ScrollSection>
          {onStartNewWorld && (
            <ActionBar
              title="Get started"
              actions={[{ id: 'new-world', label: 'Create new world', variant: 'primary' }]}
              onAction={() => onStartNewWorld()}
            />
          )}
        </section>
      )}
    </div>
  );
}

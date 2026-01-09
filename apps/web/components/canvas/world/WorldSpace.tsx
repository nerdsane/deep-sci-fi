import React from 'react';
import type { World, Story } from '@/types/dsf';
import { Hero, ScrollSection, ProgressBar, ActionBar } from '../experience';
import { InteractiveElement, type ElementType } from '../interaction';
import './world-space.css';

export interface WorldSpaceProps {
  world: World;
  stories: Story[];
  onSelectStory: (story: Story) => void;
  onExploreElement?: (elementId: string, elementType: string) => void;
  onStartNewStory?: () => void;
  onElementAction?: (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => void;
}

export const WorldSpace = React.memo(function WorldSpace({
  world,
  stories,
  onSelectStory,
  onExploreElement,
  onStartNewStory,
  onElementAction,
}: WorldSpaceProps) {
  // Default action handler that falls back to onExploreElement
  const handleAction = (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => {
    if (onElementAction) {
      onElementAction(actionId, elementId, elementType, elementData);
    } else if (onExploreElement && (actionId === 'develop' || actionId === 'explore')) {
      onExploreElement(elementId, elementType);
    }
  };
  // Guard against missing nested properties
  const foundation = world?.foundation || { core_premise: 'Unknown World', rules: [] };
  const surface = world?.surface || { visible_elements: [] };
  const development = world?.development || { version: 0, state: 'sketch' };

  // Derive world title from visible elements or premise
  const worldTitle = (() => {
    if (surface.visible_elements?.[0]?.name) {
      return surface.visible_elements[0].name;
    }
    const premise = foundation.core_premise || 'Untitled World';
    const words = premise.split(' ').slice(0, 5);
    return words.join(' ') + (words.length < premise.split(' ').length ? '...' : '');
  })();

  // Derive era from history or development state
  const worldEra = foundation.history?.eras?.[0] || development.state || 'Active';

  // Get world cover image if available
  const coverImage = world.asset?.path ? `/api/assets/${world.asset.path}` : undefined;

  // Build timeline from changelog
  const changelog = world?.changelog || [];
  const timelineEvents = changelog.slice(0, 5).map((entry, i) => ({
    id: `v${entry.version}`,
    title: `Version ${entry.version}`,
    description: entry.changes.join(', '),
    date: new Date(entry.timestamp).toLocaleDateString(),
    status: i === 0 ? 'current' as const : 'completed' as const,
  }));

  // Group visible elements by type
  const visibleElements = surface.visible_elements || [];
  const characters = visibleElements.filter(e => e.type === 'character');
  const locations = visibleElements.filter(e => e.type === 'location');
  const technologies = visibleElements.filter(e => e.type === 'technology');

  // Build actions
  const actions = [
    ...(onStartNewStory ? [{
      id: 'new-story',
      label: 'Start a new story in this world',
      variant: 'primary' as const,
    }] : []),
    ...stories.slice(0, 3).map(story => ({
      id: `story-${story.id}`,
      label: story.metadata.title,
      description: story.metadata.status === 'active' ? 'Continue reading' : 'Completed',
      variant: 'branch' as const,
    })),
  ];

  return (
    <div className="world-space">
      <ProgressBar position="top" />

      {/* Hero Section */}
      <Hero
        title={worldTitle}
        subtitle={foundation.core_premise}
        backgroundImage={coverImage}
        badge={worldEra}
        meta={[
          `${visibleElements.length} Elements`,
          `${stories.length} Stories`,
          `v${development.version || 0}`,
        ]}
        height="full"
        overlay="gradient"
      />

      {/* World Rules */}
      <section className="world-space__section">
        <ScrollSection animation="fade-up">
          <h2 className="world-space__section-title">
            <span className="world-space__section-icon">◈</span>
            Foundation Rules
          </h2>
          <div className="world-space__rules">
            {(foundation.rules || []).map((rule, i) => (
              <ScrollSection key={rule.id} animation="slide-left" delay={i * 100}>
                <InteractiveElement
                  elementType="rule"
                  elementId={rule.id}
                  elementData={rule}
                  onAction={handleAction}
                >
                  <div className="world-space__rule">
                    <span className="world-space__rule-type">{rule.certainty}</span>
                    <p className="world-space__rule-statement">{rule.statement}</p>
                  </div>
                </InteractiveElement>
              </ScrollSection>
            ))}
          </div>
        </ScrollSection>
      </section>

      {/* Characters */}
      {characters.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">◇</span>
              Characters
            </h2>
            <div className="world-space__grid">
              {characters.map((char, i) => (
                <ScrollSection key={char.id} animation="scale" delay={i * 100}>
                  <InteractiveElement
                    elementType="character"
                    elementId={char.id}
                    elementData={char}
                    onAction={handleAction}
                  >
                    <button
                      className="world-space__card"
                      onClick={() => onExploreElement?.(char.id, 'character')}
                    >
                      <h3 className="world-space__card-name">{char.name || char.id}</h3>
                      <p className="world-space__card-desc">{char.description}</p>
                      {char.first_appearance && (
                        <span className="world-space__card-meta">
                          First seen: Segment {char.first_appearance}
                        </span>
                      )}
                    </button>
                  </InteractiveElement>
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Locations */}
      {locations.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">◈</span>
              Locations
            </h2>
            <div className="world-space__grid">
              {locations.map((loc, i) => (
                <ScrollSection key={loc.id} animation="scale" delay={i * 100}>
                  <InteractiveElement
                    elementType="location"
                    elementId={loc.id}
                    elementData={loc}
                    onAction={handleAction}
                  >
                    <button
                      className="world-space__card world-space__card--location"
                      onClick={() => onExploreElement?.(loc.id, 'location')}
                    >
                      <h3 className="world-space__card-name">{loc.name || loc.id}</h3>
                      <p className="world-space__card-desc">{loc.description}</p>
                    </button>
                  </InteractiveElement>
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Technologies */}
      {technologies.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">✦</span>
              Technologies
            </h2>
            <div className="world-space__grid">
              {technologies.map((tech, i) => (
                <ScrollSection key={tech.id} animation="scale" delay={i * 100}>
                  <InteractiveElement
                    elementType="technology"
                    elementId={tech.id}
                    elementData={tech}
                    onAction={handleAction}
                  >
                    <button
                      className="world-space__card world-space__card--tech"
                      onClick={() => onExploreElement?.(tech.id, 'technology')}
                    >
                      <h3 className="world-space__card-name">{tech.name || tech.id}</h3>
                      <p className="world-space__card-desc">{tech.description}</p>
                    </button>
                  </InteractiveElement>
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Timeline / History */}
      {timelineEvents.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">○</span>
              World Evolution
            </h2>
            <div className="world-space__timeline">
              {timelineEvents.map((event, i) => (
                <ScrollSection key={event.id} animation="slide-right" delay={i * 100}>
                  <div className={`world-space__timeline-item ${event.status === 'current' ? 'world-space__timeline-item--current' : ''}`}>
                    <div className="world-space__timeline-marker" />
                    <div className="world-space__timeline-content">
                      <span className="world-space__timeline-date">{event.date}</span>
                      <h4 className="world-space__timeline-title">{event.title}</h4>
                      <p className="world-space__timeline-desc">{event.description}</p>
                    </div>
                  </div>
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Stories in this world */}
      <section className="world-space__section world-space__section--stories">
        <ScrollSection animation="fade-up">
          <h2 className="world-space__section-title">
            <span className="world-space__section-icon">→</span>
            Stories
          </h2>
          <div className="world-space__stories">
            {stories.map((story, i) => (
              <ScrollSection key={story.id} animation="fade-up" delay={i * 100}>
                <InteractiveElement
                  elementType="story_card"
                  elementId={story.id}
                  elementData={story}
                  onAction={handleAction}
                >
                  <button
                    className="world-space__story"
                    onClick={() => onSelectStory(story)}
                  >
                    <div className="world-space__story-info">
                      <h3 className="world-space__story-title">{story.metadata.title}</h3>
                      <span className="world-space__story-meta">
                        {story.segments.length} segments · {story.metadata.status}
                      </span>
                    </div>
                    <span className="world-space__story-arrow">→</span>
                  </button>
                </InteractiveElement>
              </ScrollSection>
            ))}
          </div>
        </ScrollSection>
      </section>

      {/* Actions */}
      {actions.length > 0 && (
        <ActionBar
          title="What would you like to do?"
          actions={actions}
          onAction={(actionId) => {
            if (actionId === 'new-story') {
              onStartNewStory?.();
            } else if (actionId.startsWith('story-')) {
              const storyId = actionId.replace('story-', '');
              const story = stories.find(s => s.id === storyId);
              if (story) onSelectStory(story);
            }
          }}
        />
      )}
    </div>
  );
});

/**
 * WorldSpaceEnhanced - Phase 3 Enhanced World View
 *
 * Replaces simple cards with immersive components:
 * - InteractiveWorldMap for locations
 * - TechArtifact for technologies
 * - CharacterReveal for characters
 * - StoryPortal for stories
 *
 * Integrates with existing WorldSpace data structures.
 */

import React from 'react';
import type { World, Story } from '@/types/dsf';
import { Hero, ScrollSection, ProgressBar, ActionBar } from '../experience';
import { InteractiveElement, type ElementType } from '../interaction';
import { InteractiveWorldMap, TechArtifact, CharacterReveal, StoryPortal } from './';
import type { Location } from './types';
import './world-space.css';

export interface WorldSpaceEnhancedProps {
  world: World;
  stories: Story[];
  onSelectStory: (story: Story) => void;
  onExploreElement?: (elementId: string, elementType: string) => void;
  onStartNewStory?: () => void;
  onElementAction?: (actionId: string, elementId: string, elementType: ElementType, elementData?: any) => void;
}

export const WorldSpaceEnhanced = React.memo(function WorldSpaceEnhanced({
  world,
  stories,
  onSelectStory,
  onExploreElement,
  onStartNewStory,
  onElementAction,
}: WorldSpaceEnhancedProps) {
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

  // Derive world title
  const worldTitle = (() => {
    if ((world as any).name) {
      return (world as any).name;
    }
    const premise = foundation.core_premise || 'Untitled World';
    const words = premise.split(' ').slice(0, 5);
    return words.join(' ') + (words.length < premise.split(' ').length ? '...' : '');
  })();

  const worldEra = foundation.history?.eras?.[0] || development.state || 'Active';

  // Get world cover image
  const coverImage = (() => {
    const asset = (world as any).asset;
    if (!asset) return undefined;
    if (asset.url) return asset.url;
    if (asset.path) return `/api/assets/${asset.path}`;
    return undefined;
  })();

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
  const visibleElements = Array.isArray(surface.visible_elements) ? surface.visible_elements : [];
  const characters = visibleElements.filter(e => e.type === 'character');
  const locations = visibleElements.filter(e => e.type === 'location');
  const technologies = visibleElements.filter(e => e.type === 'technology');

  // Convert locations to InteractiveWorldMap format
  const mapLocations: Location[] = locations.map((loc, index) => ({
    id: loc.id,
    name: loc.name || loc.id,
    description: loc.description,
    position: [
      0.2 + (index % 3) * 0.3, // Distribute horizontally
      0.3 + Math.floor(index / 3) * 0.3, // Distribute vertically
    ] as [number, number],
    type: 'landmark',
    discovered: true,
    icon: '📍',
  }));

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

      {/* Interactive World Map - Phase 3 Enhancement */}
      {mapLocations.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">◈</span>
              World Map
            </h2>
            <div style={{
              height: '600px',
              background: 'rgba(10, 10, 10, 0.3)',
              border: '1px solid rgba(0, 255, 204, 0.2)',
              borderRadius: '8px',
              overflow: 'hidden',
              marginTop: '1rem',
            }}>
              <InteractiveWorldMap
                worldId={world.id}
                locations={mapLocations}
                mapImageUrl={coverImage}
                showLabels={true}
                showConnections={true}
                allowZoom={true}
                allowPan={true}
                onLocationClick={(locId) => onExploreElement?.(locId, 'location')}
              />
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Technologies as TechArtifacts - Phase 3 Enhancement */}
      {technologies.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">✦</span>
              Technologies
            </h2>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
              gap: '2rem',
              marginTop: '1rem',
            }}>
              {technologies.map((tech, i) => (
                <ScrollSection key={tech.id} animation="scale" delay={i * 100}>
                  <TechArtifact
                    artifactId={tech.id}
                    name={tech.name || tech.id}
                    description={tech.description || 'No description available'}
                    category="technology"
                    rotationSpeed={0.3}
                    allowManualRotation={true}
                    onInspect={() => onExploreElement?.(tech.id, 'technology')}
                  />
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Characters as CharacterReveal - Phase 3 Enhancement */}
      {characters.length > 0 && (
        <section className="world-space__section">
          <ScrollSection animation="fade-up">
            <h2 className="world-space__section-title">
              <span className="world-space__section-icon">◉</span>
              Characters
            </h2>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
              gap: '2rem',
              marginTop: '1rem',
            }}>
              {characters.map((char, i) => (
                <ScrollSection key={char.id} animation="fade-up" delay={i * 100}>
                  <CharacterReveal
                    characterId={char.id}
                    name={char.name || char.id}
                    description={char.description || 'Mysterious figure'}
                    revealed={false}
                    revealAnimation="dramatic"
                    onClick={() => onExploreElement?.(char.id, 'character')}
                  />
                </ScrollSection>
              ))}
            </div>
          </ScrollSection>
        </section>
      )}

      {/* Stories as StoryPortals - Phase 3 Enhancement */}
      <section className="world-space__section world-space__section--stories">
        <ScrollSection animation="fade-up">
          <h2 className="world-space__section-title">
            <span className="world-space__section-icon">→</span>
            Stories
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
            gap: '2rem',
            marginTop: '1rem',
          }}>
            {stories.map((story, i) => (
              <ScrollSection key={story.id} animation="fade-up" delay={i * 100}>
                <StoryPortal
                  portalId={`portal-${story.id}`}
                  storyId={story.id}
                  title={story.metadata.title}
                  description={story.metadata.description || ''}
                  worldId={world.id}
                  badges={[
                    {
                      label: story.metadata.status === 'active' ? 'CONTINUED' : 'COMPLETE',
                      variant: story.metadata.status === 'active' ? 'continued' : 'complete',
                    },
                  ]}
                  segmentCount={story.segments.length}
                  progress={story.metadata.status === 'complete' ? 100 : 0}
                  portalType="gateway"
                  glowColor="#00ffcc"
                  animated={true}
                  onEnter={() => onSelectStory(story)}
                />
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

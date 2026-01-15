'use client';

/**
 * Phase 3 World Components Demo
 *
 * Interactive demo page to test all Phase 3 world exploration components.
 * Visit: http://localhost:3030/demo/world-components
 */

import { useState } from 'react';
import { InteractiveWorldMap, TechArtifact, CharacterReveal, StoryPortal } from '@/components/canvas/world';
import type { Location, Connection } from '@/components/canvas/world/types';

export default function WorldComponentsDemo() {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [hoveredLocation, setHoveredLocation] = useState<string | null>(null);
  const [characterRevealed, setCharacterRevealed] = useState(false);

  // Mock data for InteractiveWorldMap
  const locations: Location[] = [
    {
      id: 'neo-tokyo',
      name: 'Neo Tokyo',
      description: 'The sprawling megacity where old traditions meet cutting-edge technology',
      position: [0.3, 0.4],
      type: 'city',
      discovered: true,
      icon: '🏙️',
    },
    {
      id: 'research-station',
      name: 'Orbital Research Station',
      description: 'Zero-gravity laboratory conducting experiments on quantum entanglement',
      position: [0.7, 0.3],
      type: 'facility',
      discovered: true,
      icon: '🛰️',
    },
    {
      id: 'hidden-temple',
      name: 'Hidden Temple',
      description: 'Ancient structure with mysterious energy readings',
      position: [0.5, 0.7],
      type: 'landmark',
      discovered: false,
      locked: true,
      icon: '⛩️',
    },
    {
      id: 'wasteland',
      name: 'The Wasteland',
      description: 'Desolate zone affected by the incident',
      position: [0.2, 0.8],
      type: 'natural',
      discovered: true,
      icon: '🏜️',
    },
  ];

  const connections: Connection[] = [
    {
      id: 'conn-1',
      from: 'neo-tokyo',
      to: 'research-station',
      type: 'route',
      discovered: true,
    },
    {
      id: 'conn-2',
      from: 'neo-tokyo',
      to: 'wasteland',
      type: 'road',
      discovered: true,
    },
  ];

  return (
    <div style={{
      minHeight: '100vh',
      background: '#000000',
      color: '#c8c8c8',
      padding: '2rem',
      fontFamily: 'var(--font-sans)',
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
          <h1 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '2.5rem',
            color: '#00ffcc',
            marginBottom: '1rem',
          }}>
            Phase 3 World Components Demo
          </h1>
          <p style={{
            color: '#8a8a8a',
            maxWidth: '600px',
            margin: '0 auto',
          }}>
            Interactive demonstration of all Phase 3 world exploration components.
            Scroll down to test each component.
          </p>
        </header>

        {/* Component 1: InteractiveWorldMap */}
        <section style={{ marginBottom: '4rem' }}>
          <h2 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.5rem',
            color: '#00ffcc',
            marginBottom: '1rem',
          }}>
            1. Interactive World Map
          </h2>
          <p style={{ color: '#8a8a8a', marginBottom: '2rem' }}>
            SVG-based map with location markers, hover previews, connection paths, zoom and pan.
          </p>
          <div style={{
            height: '600px',
            background: 'rgba(10, 10, 10, 0.5)',
            border: '1px solid rgba(0, 255, 204, 0.2)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}>
            <InteractiveWorldMap
              worldId="demo-world"
              locations={locations}
              connections={connections}
              selectedLocation={selectedLocation || undefined}
              hoveredLocation={hoveredLocation || undefined}
              showLabels={true}
              showConnections={true}
              allowZoom={true}
              allowPan={true}
              onLocationClick={(locId) => {
                setSelectedLocation(locId);
                console.log('Location clicked:', locId);
              }}
              onLocationHover={(locId) => {
                setHoveredLocation(locId);
              }}
              onConnectionClick={(connId) => {
                console.log('Connection clicked:', connId);
              }}
            />
          </div>
        </section>

        {/* Component 2: TechArtifact */}
        <section style={{ marginBottom: '4rem' }}>
          <h2 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.5rem',
            color: '#00ffcc',
            marginBottom: '1rem',
          }}>
            2. Tech Artifact
          </h2>
          <p style={{ color: '#8a8a8a', marginBottom: '2rem' }}>
            Rotatable artifact with specifications and inspection mode. Drag to rotate.
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
            gap: '2rem',
          }}>
            <TechArtifact
              artifactId="quantum-core"
              name="Quantum Core"
              description="A self-sustaining quantum computer capable of processing parallel timelines. The core maintains coherence through exotic matter stabilization."
              category="technology"
              specifications={[
                { name: 'Processing Power', value: '10^18', unit: 'qubits' },
                { name: 'Coherence Time', value: '72', unit: 'hours' },
                { name: 'Power Draw', value: '2.1', unit: 'MW' },
                { name: 'Temperature', value: '-273', unit: '°C' },
              ]}
              rotationSpeed={0.3}
              allowManualRotation={true}
              scale={1}
              onInspect={() => console.log('Inspecting Quantum Core')}
              onRotate={(rot) => console.log('Rotation:', rot)}
            />

            <TechArtifact
              artifactId="neural-interface"
              name="Neural Interface"
              description="Direct brain-computer interface allowing seamless data transfer between human consciousness and digital systems."
              category="device"
              specifications={[
                { name: 'Bandwidth', value: '500', unit: 'Gbps' },
                { name: 'Latency', value: '0.1', unit: 'ms' },
                { name: 'Range', value: '100', unit: 'm' },
              ]}
              locked={false}
              rotationSpeed={0.5}
            />

            <TechArtifact
              artifactId="unknown-artifact"
              name="Unknown Artifact"
              description="Mysterious device of unknown origin. Analysis pending."
              category="technology"
              discovered={false}
            />
          </div>
        </section>

        {/* Component 3: CharacterReveal */}
        <section style={{ marginBottom: '4rem' }}>
          <h2 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.5rem',
            color: '#00ffcc',
            marginBottom: '1rem',
          }}>
            3. Character Reveal
          </h2>
          <p style={{ color: '#8a8a8a', marginBottom: '2rem' }}>
            Silhouette-to-reveal animation with character details. Click to reveal.
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '2rem',
          }}>
            <CharacterReveal
              characterId="dr-chen"
              name="Dr. Sarah Chen"
              title="Lead Quantum Physicist"
              description="Brilliant scientist who discovered the method for stable quantum entanglement. Her work revolutionized interstellar communication but came at a personal cost."
              revealed={characterRevealed}
              attributes={[
                { label: 'Age', value: '42', icon: '📅', category: 'physical' },
                { label: 'Specialization', value: 'Quantum Mechanics', icon: '⚛️', category: 'skill' },
                { label: 'Affiliation', value: 'Neo-Tokyo Research Institute', icon: '🏛️', category: 'background' },
                { label: 'Trait', value: 'Determined', icon: '💪', category: 'mental' },
              ]}
              quote="The universe doesn't care about our understanding. It simply exists."
              revealAnimation="dramatic"
              onClick={() => setCharacterRevealed(!characterRevealed)}
            />

            <CharacterReveal
              characterId="unknown-character"
              name="???"
              title="Unknown"
              description="A mysterious figure who appears in surveillance footage but has never been identified."
              silhouetteOnly={true}
            />
          </div>
        </section>

        {/* Component 4: StoryPortal */}
        <section style={{ marginBottom: '4rem' }}>
          <h2 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.5rem',
            color: '#00ffcc',
            marginBottom: '1rem',
          }}>
            4. Story Portal
          </h2>
          <p style={{ color: '#8a8a8a', marginBottom: '2rem' }}>
            Visual gateways to narratives with progress tracking and badges.
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
            gap: '2rem',
          }}>
            <StoryPortal
              portalId="portal-1"
              storyId="first-contact"
              title="First Contact"
              subtitle="The Discovery"
              description="When the quantum entanglement experiment succeeded, Dr. Chen didn't expect to receive a message from across the galaxy."
              badges={[
                { label: 'NEW', variant: 'new' },
                { label: 'Sci-Fi', variant: 'continued' },
              ]}
              segmentCount={12}
              progress={0}
              portalType="gateway"
              glowColor="#00ffcc"
              animated={true}
              onEnter={() => console.log('Entering First Contact story')}
            />

            <StoryPortal
              portalId="portal-2"
              storyId="the-incident"
              title="The Incident"
              subtitle="A Story Continued"
              description="Something went wrong at the research station. The survivors won't talk about what they saw."
              badges={[{ label: 'CONTINUED', variant: 'continued' }]}
              segmentCount={8}
              progress={65}
              lastAccessedAt={new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()}
              portalType="rift"
              glowColor="#ff8800"
              animated={true}
              onEnter={() => console.log('Continuing The Incident')}
            />

            <StoryPortal
              portalId="portal-3"
              storyId="locked-story"
              title="The Truth"
              subtitle="Locked"
              description="Complete 'The Incident' to unlock this story."
              locked={true}
              portalType="door"
            />
          </div>
        </section>

        {/* Footer */}
        <footer style={{
          marginTop: '4rem',
          paddingTop: '2rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          textAlign: 'center',
          color: '#5a5a5a',
          fontSize: '0.9rem',
        }}>
          <p>Phase 3 World Exploration Components</p>
          <p>Built for Deep Sci-Fi Immersive UX</p>
        </footer>
      </div>
    </div>
  );
}

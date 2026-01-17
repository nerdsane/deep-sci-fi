/**
 * StoryPortal3D - 3D Story Entry Gateway
 *
 * Represents a story as a dramatic portal ring
 * that users click to enter the story reader.
 */

'use client';

import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import type { StoryPortal3DProps } from './types';

// Status colors
const STATUS_COLORS: Record<string, string> = {
  active: '#00ffcc',
  complete: '#44ff88',
  draft: '#ffaa00',
  abandoned: '#ff4444',
};

export function StoryPortal3D({
  story,
  position,
  onEnter,
}: StoryPortal3DProps) {
  const groupRef = useRef<THREE.Group>(null);
  const outerRingRef = useRef<THREE.Mesh>(null);
  const innerRingRef = useRef<THREE.Mesh>(null);
  const portalRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const status = story.metadata.status || 'active';
  const color = STATUS_COLORS[status] || STATUS_COLORS.active;

  // Progress calculation
  const progress = useMemo(() => {
    if (status === 'completed') return 100;
    // Could calculate based on segments read, for now estimate
    return 0;
  }, [status]);

  // Ring animations
  useFrame((state, delta) => {
    if (groupRef.current) {
      // Gentle floating
      const offset = Math.sin(state.clock.elapsedTime * 0.5 + position[0]) * 0.08;
      groupRef.current.position.y = position[1] + offset;
    }

    if (outerRingRef.current) {
      // Outer ring rotation
      outerRingRef.current.rotation.z += delta * (hovered ? 1.5 : 0.5);
    }

    if (innerRingRef.current) {
      // Inner ring counter-rotation
      innerRingRef.current.rotation.z -= delta * (hovered ? 1.2 : 0.3);
    }

    if (portalRef.current) {
      // Portal shimmer
      const material = portalRef.current.material as THREE.MeshBasicMaterial;
      material.opacity = 0.3 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
    }
  });

  return (
    <group ref={groupRef} position={[position[0], position[1], position[2]]}>
      {/* Outer ring */}
      <mesh
        ref={outerRingRef}
        onClick={() => onEnter(story)}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <torusGeometry args={[1.4, 0.08, 16, 64]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 0.8 : 0.4}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>

      {/* Inner ring */}
      <mesh ref={innerRingRef}>
        <torusGeometry args={[1.1, 0.05, 16, 64]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 0.6 : 0.3}
          metalness={0.7}
          roughness={0.3}
        />
      </mesh>

      {/* Portal interior */}
      <mesh ref={portalRef}>
        <circleGeometry args={[1.0, 64]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.3}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Inner glow plane */}
      <mesh>
        <circleGeometry args={[0.8, 64]} />
        <meshBasicMaterial
          color="#000000"
          transparent
          opacity={0.7}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Portal light */}
      <pointLight
        color={color}
        intensity={hovered ? 4 : 1.5}
        distance={hovered ? 10 : 6}
      />

      {/* Energy particles */}
      <PortalParticles color={color} active={hovered} />

      {/* Story info */}
      <Html position={[0, -2.2, 0]} center>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
            pointerEvents: 'none',
          }}
        >
          {/* Title */}
          <div
            style={{
              padding: '8px 16px',
              background: hovered
                ? `${color}22`
                : 'rgba(0, 0, 0, 0.9)',
              border: `1px solid ${hovered ? color : 'rgba(255, 255, 255, 0.1)'}`,
              boxShadow: hovered ? `0 0 20px ${color}44` : 'none',
              transition: 'all 0.3s ease',
            }}
          >
            <h4
              style={{
                margin: 0,
                fontSize: '14px',
                color: hovered ? color : '#c8c8c8',
                fontFamily: 'var(--font-mono, monospace)',
                textAlign: 'center',
              }}
            >
              {story.metadata.title}
            </h4>
          </div>

          {/* Meta info */}
          <div
            style={{
              display: 'flex',
              gap: '12px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono, monospace)',
              color: '#666',
            }}
          >
            <span>{story.segments.length} segments</span>
            <span
              style={{
                color: color,
                textTransform: 'uppercase',
              }}
            >
              {status}
            </span>
          </div>

          {/* Progress bar */}
          {progress > 0 && progress < 100 && (
            <div
              style={{
                width: '120px',
                height: '3px',
                background: 'rgba(255, 255, 255, 0.1)',
              }}
            >
              <div
                style={{
                  width: `${progress}%`,
                  height: '100%',
                  background: color,
                }}
              />
            </div>
          )}

          {/* Hover info */}
          {hovered && (
            <div
              style={{
                padding: '12px 16px',
                background: 'rgba(10, 10, 10, 0.95)',
                border: `1px solid ${color}`,
                maxWidth: '260px',
                marginTop: '8px',
              }}
            >
              {story.metadata.author_notes && (
                <p
                  style={{
                    margin: '0 0 10px 0',
                    fontSize: '12px',
                    color: '#aaa',
                    lineHeight: 1.4,
                  }}
                >
                  {story.metadata.author_notes}
                </p>
              )}

              <div
                style={{
                  fontSize: '10px',
                  color: color,
                  fontFamily: 'var(--font-mono, monospace)',
                  textAlign: 'center',
                  paddingTop: '10px',
                  borderTop: `1px solid ${color}33`,
                }}
              >
                CLICK TO ENTER STORY
              </div>
            </div>
          )}
        </div>
      </Html>
    </group>
  );
}

/**
 * PortalParticles - Energy particles around the portal
 */
function PortalParticles({ color, active }: { color: string; active: boolean }) {
  const particlesRef = useRef<THREE.Points>(null);

  const { positions, velocities } = useMemo(() => {
    const count = 40;
    const positions = new Float32Array(count * 3);
    const velocities: THREE.Vector3[] = [];

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const radius = 1.2 + Math.random() * 0.3;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = Math.sin(angle) * radius;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 0.3;

      velocities.push(
        new THREE.Vector3(
          Math.cos(angle) * 0.02,
          Math.sin(angle) * 0.02,
          (Math.random() - 0.5) * 0.01
        )
      );
    }

    return { positions, velocities };
  }, []);

  useFrame(() => {
    if (particlesRef.current && active) {
      const posArray = particlesRef.current.geometry.attributes.position
        .array as Float32Array;

      for (let i = 0; i < velocities.length; i++) {
        posArray[i * 3] += velocities[i].x;
        posArray[i * 3 + 1] += velocities[i].y;
        posArray[i * 3 + 2] += velocities[i].z;

        // Reset if too far
        const dist = Math.sqrt(
          posArray[i * 3] ** 2 + posArray[i * 3 + 1] ** 2
        );
        if (dist > 2) {
          const angle = (i / velocities.length) * Math.PI * 2;
          posArray[i * 3] = Math.cos(angle) * 1.2;
          posArray[i * 3 + 1] = Math.sin(angle) * 1.2;
        }
      }

      particlesRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={40}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color={color}
        size={active ? 0.08 : 0.04}
        transparent
        opacity={active ? 0.8 : 0.3}
        sizeAttenuation
      />
    </points>
  );
}

export default StoryPortal3D;

/**
 * LocationNode - 3D Location Point of Interest
 *
 * Represents a location in the world as an interactive
 * glowing orb that users can fly to.
 */

'use client';

import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, Sphere } from '@react-three/drei';
import * as THREE from 'three';
import type { LocationNodeProps, WorldLocation } from './types';

// Location type colors
const LOCATION_COLORS: Record<WorldLocation['type'], string> = {
  city: '#00ffcc',
  facility: '#00aaff',
  landmark: '#ffaa00',
  natural: '#44ff88',
  unknown: '#888888',
};

// Location type icons
const LOCATION_ICONS: Record<WorldLocation['type'], string> = {
  city: '🏙️',
  facility: '🏛️',
  landmark: '⛩️',
  natural: '🌿',
  unknown: '❓',
};

export function LocationNode({
  location,
  position,
  isSelected,
  onSelect,
  onFlyTo,
}: LocationNodeProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const color = useMemo(
    () => LOCATION_COLORS[location.type] || LOCATION_COLORS.unknown,
    [location.type]
  );

  const icon = useMemo(
    () => location.icon || LOCATION_ICONS[location.type] || '📍',
    [location.icon, location.type]
  );

  // Floating animation
  useFrame((state) => {
    if (groupRef.current) {
      // Gentle bob
      const offset = Math.sin(state.clock.elapsedTime * 0.7 + position[0] * 2) * 0.15;
      groupRef.current.position.y = position[1] + offset;
    }

    if (ringRef.current) {
      // Ring rotation
      ringRef.current.rotation.z += 0.01;
      ringRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.2;
    }
  });

  // Handle click - fly camera to this location
  const handleClick = () => {
    if (location.locked) return;

    onSelect(location.id);

    // Calculate viewing position (offset from location)
    const targetPos = new THREE.Vector3(...position);
    const viewPos = new THREE.Vector3(
      position[0] + 4,
      position[1] + 2,
      position[2] + 5
    );

    onFlyTo(viewPos, targetPos);
  };

  // Locked state
  if (location.locked) {
    return (
      <group position={position}>
        <mesh>
          <sphereGeometry args={[0.4, 16, 16]} />
          <meshStandardMaterial
            color="#333333"
            transparent
            opacity={0.5}
          />
        </mesh>
        <Html center>
          <div
            style={{
              padding: '4px 8px',
              background: 'rgba(0, 0, 0, 0.8)',
              border: '1px solid #444',
              color: '#666',
              fontSize: '10px',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            🔒 LOCKED
          </div>
        </Html>
      </group>
    );
  }

  return (
    <group ref={groupRef} position={[position[0], position[1], position[2]]}>
      {/* Main sphere */}
      <Sphere
        ref={meshRef}
        args={[0.5, 32, 32]}
        onClick={handleClick}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
        scale={hovered ? 1.3 : isSelected ? 1.2 : 1}
      >
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 0.8 : isSelected ? 0.6 : 0.3}
          metalness={0.3}
          roughness={0.4}
        />
      </Sphere>

      {/* Orbital ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.8, 0.02, 16, 64]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={hovered ? 0.6 : 0.2}
        />
      </mesh>

      {/* Glow light */}
      <pointLight
        color={color}
        intensity={hovered ? 2.5 : isSelected ? 2 : 1}
        distance={hovered ? 8 : 5}
      />

      {/* Label */}
      <Html position={[0, 1.2, 0]} center>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            pointerEvents: 'none',
          }}
        >
          {/* Icon */}
          <span
            style={{
              fontSize: '20px',
              filter: hovered ? 'drop-shadow(0 0 8px rgba(0, 255, 204, 0.8))' : 'none',
              transform: hovered ? 'scale(1.2)' : 'scale(1)',
              transition: 'all 0.3s ease',
            }}
          >
            {icon}
          </span>

          {/* Name */}
          <div
            style={{
              padding: '4px 12px',
              background: hovered
                ? 'rgba(0, 255, 204, 0.15)'
                : 'rgba(0, 0, 0, 0.8)',
              border: `1px solid ${hovered ? color : 'rgba(255, 255, 255, 0.1)'}`,
              color: hovered ? color : '#c8c8c8',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              whiteSpace: 'nowrap',
              transition: 'all 0.3s ease',
            }}
          >
            {location.name}
          </div>
        </div>
      </Html>

      {/* Expanded info when selected or hovered */}
      {(isSelected || hovered) && (
        <Html position={[0, -1.5, 0]} center>
          <div
            style={{
              padding: '12px 16px',
              background: 'rgba(10, 10, 10, 0.95)',
              border: `1px solid ${color}`,
              maxWidth: '220px',
              boxShadow: `0 0 20px ${color}33`,
            }}
          >
            <div
              style={{
                fontSize: '10px',
                color: color,
                marginBottom: '6px',
                fontFamily: 'var(--font-mono, monospace)',
                textTransform: 'uppercase',
              }}
            >
              {location.type}
            </div>
            <p
              style={{
                margin: 0,
                fontSize: '12px',
                color: '#aaa',
                lineHeight: 1.4,
              }}
            >
              {location.description}
            </p>
            {hovered && !isSelected && (
              <div
                style={{
                  marginTop: '10px',
                  paddingTop: '10px',
                  borderTop: `1px solid ${color}33`,
                  fontSize: '10px',
                  color: color,
                  fontFamily: 'var(--font-mono, monospace)',
                  textAlign: 'center',
                }}
              >
                CLICK TO FLY HERE
              </div>
            )}
          </div>
        </Html>
      )}

      {/* Particle effect when hovered */}
      {hovered && <LocationParticles color={color} />}
    </group>
  );
}

/**
 * LocationParticles - Particle effect around location when hovered
 */
function LocationParticles({ color }: { color: string }) {
  const particlesRef = useRef<THREE.Points>(null);

  const particlePositions = useMemo(() => {
    const positions = new Float32Array(30 * 3);
    for (let i = 0; i < 30; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;
      const r = 0.8 + Math.random() * 0.4;
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
    }
    return positions;
  }, []);

  useFrame((state) => {
    if (particlesRef.current) {
      particlesRef.current.rotation.y += 0.02;
      particlesRef.current.rotation.x = Math.sin(state.clock.elapsedTime) * 0.1;
    }
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={30}
          array={particlePositions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color={color}
        size={0.05}
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  );
}

export default LocationNode;

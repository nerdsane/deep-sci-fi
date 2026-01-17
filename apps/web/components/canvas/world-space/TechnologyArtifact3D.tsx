/**
 * TechnologyArtifact3D - 3D Technology Object
 *
 * Represents a technology as a rotating 3D artifact
 * that users can inspect.
 */

'use client';

import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import type { TechnologyArtifact3DProps, WorldTechnology } from './types';

// Category-based geometry and colors
const CATEGORY_CONFIG: Record<
  NonNullable<WorldTechnology['category']>,
  { color: string; emissive: string; geometry: 'icosahedron' | 'octahedron' | 'box' | 'cylinder' | 'cone' | 'torus' }
> = {
  device: { color: '#ff8800', emissive: '#ff4400', geometry: 'box' },
  vehicle: { color: '#00aaff', emissive: '#0066aa', geometry: 'cone' },
  weapon: { color: '#ff4444', emissive: '#aa0000', geometry: 'cylinder' },
  infrastructure: { color: '#8844ff', emissive: '#4400aa', geometry: 'torus' },
  material: { color: '#44ff88', emissive: '#00aa44', geometry: 'octahedron' },
  technology: { color: '#ffaa00', emissive: '#aa6600', geometry: 'icosahedron' },
};

// Category icons
const CATEGORY_ICONS: Record<NonNullable<WorldTechnology['category']>, string> = {
  device: '📱',
  vehicle: '🚀',
  weapon: '⚔️',
  infrastructure: '🏗️',
  material: '💎',
  technology: '⚡',
};

export function TechnologyArtifact3D({
  tech,
  position,
  onInspect,
}: TechnologyArtifact3DProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const rotationVelocity = useRef({ x: 0, y: 0 });

  const config = useMemo(
    () => CATEGORY_CONFIG[tech.category || 'technology'] || CATEGORY_CONFIG.technology,
    [tech.category]
  );

  const icon = useMemo(
    () => CATEGORY_ICONS[tech.category || 'technology'] || '✦',
    [tech.category]
  );

  // Auto-rotation and floating
  useFrame((state, delta) => {
    if (groupRef.current) {
      // Floating animation
      const offset = Math.sin(state.clock.elapsedTime * 0.6 + position[0]) * 0.1;
      groupRef.current.position.y = position[1] + offset;
    }

    if (meshRef.current && !isDragging) {
      // Auto-rotation (slower when hovered)
      const rotSpeed = hovered ? 0.3 : 0.5;
      meshRef.current.rotation.y += delta * rotSpeed;
      meshRef.current.rotation.x += delta * 0.2;

      // Apply drag velocity decay
      if (rotationVelocity.current.x !== 0 || rotationVelocity.current.y !== 0) {
        meshRef.current.rotation.y += rotationVelocity.current.y;
        meshRef.current.rotation.x += rotationVelocity.current.x;
        rotationVelocity.current.x *= 0.95;
        rotationVelocity.current.y *= 0.95;
        if (Math.abs(rotationVelocity.current.x) < 0.001) rotationVelocity.current.x = 0;
        if (Math.abs(rotationVelocity.current.y) < 0.001) rotationVelocity.current.y = 0;
      }
    }
  });

  // Render geometry based on category
  const geometry = useMemo(() => {
    switch (config.geometry) {
      case 'box':
        return <boxGeometry args={[0.6, 0.4, 0.5]} />;
      case 'cone':
        return <coneGeometry args={[0.35, 0.8, 6]} />;
      case 'cylinder':
        return <cylinderGeometry args={[0.15, 0.2, 0.8, 8]} />;
      case 'torus':
        return <torusGeometry args={[0.35, 0.12, 16, 32]} />;
      case 'octahedron':
        return <octahedronGeometry args={[0.45]} />;
      case 'icosahedron':
      default:
        return <icosahedronGeometry args={[0.4, 0]} />;
    }
  }, [config.geometry]);

  // Locked state
  if (tech.locked) {
    return (
      <group position={position}>
        <mesh>
          <boxGeometry args={[0.4, 0.4, 0.4]} />
          <meshStandardMaterial color="#333333" transparent opacity={0.4} />
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
            🔒 CLASSIFIED
          </div>
        </Html>
      </group>
    );
  }

  return (
    <group ref={groupRef} position={[position[0], position[1], position[2]]}>
      {/* Artifact mesh */}
      <mesh
        ref={meshRef}
        onClick={() => onInspect(tech)}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => {
          setHovered(false);
          setIsDragging(false);
        }}
        onPointerDown={() => setIsDragging(true)}
        onPointerUp={() => setIsDragging(false)}
        scale={hovered ? 1.3 : 1}
      >
        {geometry}
        <meshStandardMaterial
          color={config.color}
          emissive={config.emissive}
          emissiveIntensity={hovered ? 0.7 : 0.4}
          metalness={0.7}
          roughness={0.3}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh ref={meshRef} scale={hovered ? 1.35 : 1.05}>
        {geometry}
        <meshBasicMaterial
          color={config.color}
          wireframe
          transparent
          opacity={hovered ? 0.4 : 0.15}
        />
      </mesh>

      {/* Glow light */}
      <pointLight
        color={config.color}
        intensity={hovered ? 2 : 0.8}
        distance={hovered ? 6 : 4}
      />

      {/* Label */}
      <Html position={[0, 1, 0]} center>
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
              fontSize: '18px',
              filter: hovered ? `drop-shadow(0 0 8px ${config.color})` : 'none',
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
                ? `${config.color}22`
                : 'rgba(0, 0, 0, 0.8)',
              border: `1px solid ${hovered ? config.color : 'rgba(255, 255, 255, 0.1)'}`,
              color: hovered ? config.color : '#c8c8c8',
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              whiteSpace: 'nowrap',
              transition: 'all 0.3s ease',
            }}
          >
            {tech.name}
          </div>
        </div>
      </Html>

      {/* Hover tooltip */}
      {hovered && (
        <Html position={[0, -1.3, 0]} center>
          <div
            style={{
              padding: '12px 16px',
              background: 'rgba(10, 10, 10, 0.95)',
              border: `1px solid ${config.color}`,
              maxWidth: '240px',
              boxShadow: `0 0 20px ${config.color}33`,
            }}
          >
            {/* Category badge */}
            <div
              style={{
                display: 'inline-block',
                padding: '2px 8px',
                marginBottom: '8px',
                fontSize: '9px',
                fontFamily: 'var(--font-mono, monospace)',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: config.color,
                border: `1px solid ${config.color}`,
              }}
            >
              {tech.category || 'technology'}
            </div>

            {/* Description */}
            <p
              style={{
                margin: '0 0 8px 0',
                fontSize: '12px',
                color: '#aaa',
                lineHeight: 1.4,
              }}
            >
              {tech.description}
            </p>

            {/* Specs preview */}
            {tech.specifications && tech.specifications.length > 0 && (
              <div
                style={{
                  paddingTop: '8px',
                  borderTop: `1px solid ${config.color}33`,
                }}
              >
                {tech.specifications.slice(0, 2).map((spec, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '10px',
                      color: '#666',
                      marginBottom: '2px',
                    }}
                  >
                    <span>{spec.name}</span>
                    <span style={{ color: config.color }}>
                      {spec.value}
                      {spec.unit && ` ${spec.unit}`}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Click hint */}
            <div
              style={{
                marginTop: '10px',
                paddingTop: '10px',
                borderTop: `1px solid ${config.color}33`,
                fontSize: '10px',
                color: config.color,
                fontFamily: 'var(--font-mono, monospace)',
                textAlign: 'center',
              }}
            >
              CLICK TO INSPECT
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

export default TechnologyArtifact3D;

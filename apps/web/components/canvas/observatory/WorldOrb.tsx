'use client';

import { useRef, useState, useMemo } from 'react';
import { useFrame, useLoader } from '@react-three/fiber';
import { Sphere, Ring, Html } from '@react-three/drei';
import * as THREE from 'three';
import type { World } from '@/types/dsf';

interface WorldOrbProps {
  world: World;
  position: [number, number, number];
  onClick: (world: World, position: THREE.Vector3) => void;
  onHover?: (world: World | null) => void;
}

// Particle ring around the world
function OrbitalParticles({ radius, count, color }: { radius: number; count: number; color: string }) {
  const particlesRef = useRef<THREE.Points>(null);

  const [positions, speeds] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const spd = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const r = radius + (Math.random() - 0.5) * 0.3;
      const height = (Math.random() - 0.5) * 0.5;

      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = height;
      pos[i * 3 + 2] = Math.sin(angle) * r;
      spd[i] = 0.2 + Math.random() * 0.3;
    }

    return [pos, spd];
  }, [count, radius]);

  useFrame((state, delta) => {
    if (!particlesRef.current) return;

    const positions = particlesRef.current.geometry.attributes.position.array as Float32Array;

    for (let i = 0; i < count; i++) {
      const angle = Math.atan2(positions[i * 3 + 2], positions[i * 3]);
      const r = Math.sqrt(positions[i * 3] ** 2 + positions[i * 3 + 2] ** 2);
      const newAngle = angle + delta * speeds[i];

      positions[i * 3] = Math.cos(newAngle) * r;
      positions[i * 3 + 2] = Math.sin(newAngle) * r;
    }

    particlesRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.05}
        color={color}
        transparent
        opacity={0.8}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// Glow effect behind the sphere
function GlowEffect({ color, intensity }: { color: string; intensity: number }) {
  return (
    <Sphere args={[1.2, 32, 32]}>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.15 * intensity}
        side={THREE.BackSide}
      />
    </Sphere>
  );
}

export function WorldOrb({ world, position, onClick, onHover }: WorldOrbProps) {
  const groupRef = useRef<THREE.Group>(null);
  const sphereRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);

  // Get world cover image
  const coverUrl = useMemo(() => {
    const asset = (world as any).asset;
    if (!asset) return null;
    if (asset.url) return asset.url;
    if (asset.path) return `/api/assets/${asset.path}`;
    return null;
  }, [world]);

  // Load texture if cover exists
  useMemo(() => {
    if (coverUrl) {
      const loader = new THREE.TextureLoader();
      loader.load(
        coverUrl,
        (tex) => {
          tex.colorSpace = THREE.SRGBColorSpace;
          setTexture(tex);
        },
        undefined,
        () => setTexture(null)
      );
    }
  }, [coverUrl]);

  // World color based on development state
  const worldColor = useMemo(() => {
    const state = world.development?.state || 'sketch';
    switch (state) {
      case 'detailed': return '#00ffcc';
      case 'draft': return '#00ccff';
      default: return '#8888ff';
    }
  }, [world.development?.state]);

  // Animate the orb
  useFrame((state, delta) => {
    if (!groupRef.current) return;

    // Gentle rotation
    groupRef.current.rotation.y += delta * 0.1;

    // Hover scale animation
    const targetScale = hovered ? 1.2 : 1;
    groupRef.current.scale.lerp(
      new THREE.Vector3(targetScale, targetScale, targetScale),
      delta * 5
    );

    // Gentle bobbing
    if (sphereRef.current) {
      sphereRef.current.position.y = Math.sin(state.clock.elapsedTime + position[0]) * 0.1;
    }
  });

  const handleClick = (e: any) => {
    e.stopPropagation();
    const worldPosition = new THREE.Vector3(...position);
    onClick(world, worldPosition);
  };

  const handlePointerOver = (e: any) => {
    e.stopPropagation();
    setHovered(true);
    onHover?.(world);
    document.body.style.cursor = 'pointer';
  };

  const handlePointerOut = () => {
    setHovered(false);
    onHover?.(null);
    document.body.style.cursor = 'default';
  };

  return (
    <group ref={groupRef} position={position}>
      {/* Glow effect */}
      <GlowEffect color={worldColor} intensity={hovered ? 2 : 1} />

      {/* Main sphere */}
      <Sphere
        ref={sphereRef}
        args={[1, 64, 64]}
        onClick={handleClick}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
      >
        {texture ? (
          <meshStandardMaterial
            map={texture}
            emissive={worldColor}
            emissiveIntensity={hovered ? 0.3 : 0.1}
            roughness={0.7}
            metalness={0.3}
          />
        ) : (
          <meshStandardMaterial
            color={worldColor}
            emissive={worldColor}
            emissiveIntensity={hovered ? 0.5 : 0.2}
            roughness={0.4}
            metalness={0.6}
            wireframe={false}
          />
        )}
      </Sphere>

      {/* Orbital particles */}
      <OrbitalParticles radius={1.5} count={50} color={worldColor} />

      {/* Orbital ring */}
      <Ring
        args={[1.4, 1.5, 64]}
        rotation={[Math.PI / 2, 0, 0]}
      >
        <meshBasicMaterial
          color={worldColor}
          transparent
          opacity={hovered ? 0.4 : 0.2}
          side={THREE.DoubleSide}
        />
      </Ring>

      {/* Second tilted ring */}
      <Ring
        args={[1.6, 1.65, 64]}
        rotation={[Math.PI / 3, Math.PI / 4, 0]}
      >
        <meshBasicMaterial
          color={worldColor}
          transparent
          opacity={hovered ? 0.3 : 0.1}
          side={THREE.DoubleSide}
        />
      </Ring>
    </group>
  );
}

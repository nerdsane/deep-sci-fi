'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface StarFieldProps {
  count?: number;
  radius?: number;
}

export function StarField({ count = 2000, radius = 100 }: StarFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);

  // Generate star positions and properties
  const [positions, colors, sizes, twinkleOffsets] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const siz = new Float32Array(count);
    const twinkle = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Spherical distribution
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = radius * (0.5 + Math.random() * 0.5);

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Color variation (mostly white with hints of cyan/purple)
      const colorType = Math.random();
      if (colorType < 0.7) {
        // White/silver stars
        col[i * 3] = 0.9 + Math.random() * 0.1;
        col[i * 3 + 1] = 0.9 + Math.random() * 0.1;
        col[i * 3 + 2] = 1.0;
      } else if (colorType < 0.85) {
        // Cyan tinted
        col[i * 3] = 0.0;
        col[i * 3 + 1] = 0.8 + Math.random() * 0.2;
        col[i * 3 + 2] = 0.8 + Math.random() * 0.2;
      } else {
        // Purple tinted
        col[i * 3] = 0.6 + Math.random() * 0.3;
        col[i * 3 + 1] = 0.0;
        col[i * 3 + 2] = 0.8 + Math.random() * 0.2;
      }

      // Size variation
      siz[i] = 0.5 + Math.random() * 1.5;

      // Twinkle offset for animation
      twinkle[i] = Math.random() * Math.PI * 2;
    }

    return [pos, col, siz, twinkle];
  }, [count, radius]);

  // Animate twinkling
  useFrame((state) => {
    if (!pointsRef.current) return;

    const sizes = pointsRef.current.geometry.attributes.size.array as Float32Array;
    const time = state.clock.elapsedTime;

    for (let i = 0; i < count; i++) {
      // Subtle twinkle effect
      const twinkle = 0.8 + 0.2 * Math.sin(time * 2 + twinkleOffsets[i]);
      sizes[i] = (0.5 + Math.random() * 1.5) * twinkle;
    }

    pointsRef.current.geometry.attributes.size.needsUpdate = true;

    // Slow rotation of entire star field
    pointsRef.current.rotation.y = time * 0.01;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[colors, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[sizes, 1]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={1}
        vertexColors
        transparent
        opacity={0.9}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

// Nebula clouds in background
export function NebulaCloud({ position, color, size }: {
  position: [number, number, number];
  color: string;
  size: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.z = state.clock.elapsedTime * 0.05;
  });

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[size, 32, 32]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.05}
        side={THREE.BackSide}
      />
    </mesh>
  );
}

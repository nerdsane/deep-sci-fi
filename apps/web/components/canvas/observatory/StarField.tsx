'use client';

import { useRef, useMemo } from 'react';
import { useFrame, extend } from '@react-three/fiber';
import * as THREE from 'three';

// Custom shader material for soft, glowing stars
const SoftStarMaterial = {
  uniforms: {
    time: { value: 0 },
    opacity: { value: 1.0 },
  },
  vertexShader: `
    attribute float size;
    attribute float twinkle;
    attribute vec3 customColor;
    varying vec3 vColor;
    varying float vTwinkle;
    uniform float time;

    void main() {
      vColor = customColor;
      vTwinkle = twinkle;

      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);

      // Twinkle effect
      float twinkleAmount = 0.7 + 0.3 * sin(time * 1.5 + twinkle * 6.28);

      gl_PointSize = size * twinkleAmount * (300.0 / -mvPosition.z);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying vec3 vColor;
    varying float vTwinkle;
    uniform float opacity;

    void main() {
      // Ultra-soft circular gradient - nebula/mist look
      vec2 center = gl_PointCoord - vec2(0.5);
      float dist = length(center);

      // Gaussian-like falloff for maximum softness
      float gaussian = exp(-dist * dist * 8.0);

      // Multiple soft layers blending outward
      float core = 1.0 - smoothstep(0.0, 0.1, dist);
      float inner = 1.0 - smoothstep(0.0, 0.25, dist);
      float glow = 1.0 - smoothstep(0.0, 0.4, dist);
      float haze = 1.0 - smoothstep(0.0, 0.5, dist);

      // Combine for ultra-soft, misty glow
      float alpha = gaussian * 0.6 + core * 0.3 + inner * 0.2 + glow * 0.15 + haze * 0.1;

      // Nebula color shift - more purple/cyan in the haze
      vec3 hazeColor = mix(vec3(0.6, 0.4, 0.8), vec3(0.3, 0.7, 0.9), vTwinkle);
      vec3 glowColor = mix(vColor, hazeColor, haze * 0.5);

      if (alpha < 0.005) discard;

      gl_FragColor = vec4(glowColor, alpha * opacity * 0.8);
    }
  `,
};

interface StarFieldProps {
  count?: number;
  radius?: number;
}

export function StarField({ count = 3000, radius = 100 }: StarFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // Generate star positions and properties
  const [positions, colors, sizes, twinkles] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const siz = new Float32Array(count);
    const twk = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Spherical distribution with some clustering
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = radius * (0.3 + Math.random() * 0.7);

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Softer color palette - more pastel/nebula-like
      const colorType = Math.random();
      if (colorType < 0.5) {
        // Soft white/blue
        col[i * 3] = 0.8 + Math.random() * 0.2;
        col[i * 3 + 1] = 0.85 + Math.random() * 0.15;
        col[i * 3 + 2] = 1.0;
      } else if (colorType < 0.75) {
        // Soft cyan/teal
        col[i * 3] = 0.4 + Math.random() * 0.3;
        col[i * 3 + 1] = 0.7 + Math.random() * 0.3;
        col[i * 3 + 2] = 0.8 + Math.random() * 0.2;
      } else if (colorType < 0.9) {
        // Soft purple/pink
        col[i * 3] = 0.6 + Math.random() * 0.3;
        col[i * 3 + 1] = 0.4 + Math.random() * 0.2;
        col[i * 3 + 2] = 0.8 + Math.random() * 0.2;
      } else {
        // Warm gold/orange (rare)
        col[i * 3] = 0.9 + Math.random() * 0.1;
        col[i * 3 + 1] = 0.7 + Math.random() * 0.2;
        col[i * 3 + 2] = 0.4 + Math.random() * 0.2;
      }

      // Larger, more varied sizes for softer look
      siz[i] = 2 + Math.random() * 6;

      // Twinkle phase offset
      twk[i] = Math.random();
    }

    return [pos, col, siz, twk];
  }, [count, radius]);

  // Animate
  useFrame((state) => {
    if (!pointsRef.current || !materialRef.current) return;

    // Update shader time uniform
    materialRef.current.uniforms.time.value = state.clock.elapsedTime;

    // Slow rotation of entire star field
    pointsRef.current.rotation.y = state.clock.elapsedTime * 0.008;
    pointsRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.01) * 0.02;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-customColor"
          args={[colors, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[sizes, 1]}
        />
        <bufferAttribute
          attach="attributes-twinkle"
          args={[twinkles, 1]}
        />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        args={[SoftStarMaterial]}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// Soft nebula clouds in background
export function NebulaClouds() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.01;
  });

  // Create multiple soft, overlapping cloud spheres
  const clouds = useMemo(() => {
    const result = [];
    const colors = ['#1a3a5c', '#2d1a4a', '#0d2a3a', '#1a2d4a'];

    for (let i = 0; i < 8; i++) {
      const theta = (i / 8) * Math.PI * 2;
      const radius = 40 + Math.random() * 20;
      const size = 15 + Math.random() * 15;

      result.push({
        position: [
          Math.cos(theta) * radius,
          (Math.random() - 0.5) * 30,
          Math.sin(theta) * radius,
        ] as [number, number, number],
        size,
        color: colors[Math.floor(Math.random() * colors.length)],
        opacity: 0.03 + Math.random() * 0.03,
      });
    }

    return result;
  }, []);

  return (
    <group ref={groupRef}>
      {clouds.map((cloud, i) => (
        <mesh key={i} position={cloud.position}>
          <sphereGeometry args={[cloud.size, 32, 32]} />
          <meshBasicMaterial
            color={cloud.color}
            transparent
            opacity={cloud.opacity}
            side={THREE.BackSide}
          />
        </mesh>
      ))}
    </group>
  );
}

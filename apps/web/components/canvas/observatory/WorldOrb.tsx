'use client';

import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere } from '@react-three/drei';
import * as THREE from 'three';
import type { World } from '@/types/dsf';

interface WorldOrbProps {
  world: World;
  position: [number, number, number];
  onClick: (world: World, position: THREE.Vector3) => void;
  onHover?: (world: World | null) => void;
}

// Soft, multi-layered atmospheric glow
function AtmosphericGlow({ color, intensity, hovered }: { color: string; intensity: number; hovered: boolean }) {
  const layers = useMemo(() => {
    const baseIntensity = hovered ? intensity * 1.5 : intensity;
    return [
      { scale: 1.15, opacity: 0.25 * baseIntensity },
      { scale: 1.35, opacity: 0.15 * baseIntensity },
      { scale: 1.6, opacity: 0.08 * baseIntensity },
      { scale: 2.0, opacity: 0.04 * baseIntensity },
      { scale: 2.5, opacity: 0.02 * baseIntensity },
    ];
  }, [intensity, hovered]);

  return (
    <group>
      {layers.map((layer, i) => (
        <Sphere key={i} args={[layer.scale, 32, 32]}>
          <meshBasicMaterial
            color={color}
            transparent
            opacity={layer.opacity}
            side={THREE.BackSide}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </Sphere>
      ))}
    </group>
  );
}

// Soft orbital particles using shader for smooth appearance
function SoftOrbitalParticles({ radius, count, color }: { radius: number; count: number; color: string }) {
  const particlesRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const [positions, speeds, sizes] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const spd = new Float32Array(count);
    const siz = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const r = radius + (Math.random() - 0.5) * 0.4;
      const height = (Math.random() - 0.5) * 0.6;

      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = height;
      pos[i * 3 + 2] = Math.sin(angle) * r;
      spd[i] = 0.15 + Math.random() * 0.25;
      siz[i] = 3 + Math.random() * 5;
    }

    return [pos, spd, siz];
  }, [count, radius]);

  // Custom soft particle shader
  const softParticleMaterial = useMemo(() => ({
    uniforms: {
      color: { value: new THREE.Color(color) },
      opacity: { value: 0.6 },
    },
    vertexShader: `
      attribute float size;
      varying float vSize;

      void main() {
        vSize = size;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * (200.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      uniform vec3 color;
      uniform float opacity;

      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);

        // Very soft falloff
        float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
        alpha = alpha * alpha; // Quadratic falloff for extra softness

        if (alpha < 0.01) discard;

        gl_FragColor = vec4(color, alpha * opacity);
      }
    `,
  }), [color]);

  useFrame((state, delta) => {
    if (!particlesRef.current) return;

    const posArray = particlesRef.current.geometry.attributes.position.array as Float32Array;

    for (let i = 0; i < count; i++) {
      const angle = Math.atan2(posArray[i * 3 + 2], posArray[i * 3]);
      const r = Math.sqrt(posArray[i * 3] ** 2 + posArray[i * 3 + 2] ** 2);
      const newAngle = angle + delta * speeds[i];

      posArray[i * 3] = Math.cos(newAngle) * r;
      posArray[i * 3 + 2] = Math.sin(newAngle) * r;
    }

    particlesRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        args={[softParticleMaterial]}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// Soft glowing ring
function SoftRing({ innerRadius, outerRadius, color, opacity, rotation }: {
  innerRadius: number;
  outerRadius: number;
  color: string;
  opacity: number;
  rotation: [number, number, number];
}) {
  return (
    <mesh rotation={rotation}>
      <ringGeometry args={[innerRadius, outerRadius, 128]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.DoubleSide}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
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

  // World color based on development state - softer palette
  const worldColor = useMemo(() => {
    const state = world.development?.state || 'sketch';
    switch (state) {
      case 'detailed': return '#40e0d0'; // Soft turquoise
      case 'draft': return '#87ceeb'; // Soft sky blue
      default: return '#b8a9c9'; // Soft lavender
    }
  }, [world.development?.state]);

  // Animate the orb
  useFrame((state, delta) => {
    if (!groupRef.current) return;

    // Gentle rotation
    groupRef.current.rotation.y += delta * 0.08;

    // Smooth hover scale animation
    const targetScale = hovered ? 1.15 : 1;
    groupRef.current.scale.lerp(
      new THREE.Vector3(targetScale, targetScale, targetScale),
      delta * 4
    );

    // Gentle floating
    if (sphereRef.current) {
      sphereRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5 + position[0]) * 0.08;
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
      {/* Multi-layered atmospheric glow */}
      <AtmosphericGlow color={worldColor} intensity={1} hovered={hovered} />

      {/* Main sphere with soft material */}
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
            emissiveIntensity={hovered ? 0.4 : 0.2}
            roughness={0.8}
            metalness={0.1}
          />
        ) : (
          <meshStandardMaterial
            color={worldColor}
            emissive={worldColor}
            emissiveIntensity={hovered ? 0.6 : 0.3}
            roughness={0.6}
            metalness={0.2}
          />
        )}
      </Sphere>

      {/* Inner core glow for extra luminosity */}
      <Sphere args={[0.95, 32, 32]}>
        <meshBasicMaterial
          color={worldColor}
          transparent
          opacity={hovered ? 0.3 : 0.15}
          blending={THREE.AdditiveBlending}
        />
      </Sphere>

      {/* Soft orbital particles */}
      <SoftOrbitalParticles radius={1.6} count={40} color={worldColor} />

      {/* Soft, diffuse rings */}
      <SoftRing
        innerRadius={1.4}
        outerRadius={1.7}
        color={worldColor}
        opacity={hovered ? 0.25 : 0.12}
        rotation={[Math.PI / 2, 0, 0]}
      />
      <SoftRing
        innerRadius={1.7}
        outerRadius={1.9}
        color={worldColor}
        opacity={hovered ? 0.15 : 0.06}
        rotation={[Math.PI / 2.5, Math.PI / 5, 0]}
      />
    </group>
  );
}

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

// Custom soft planet shader with fresnel edge glow
const SoftPlanetMaterial = {
  uniforms: {
    baseColor: { value: new THREE.Color('#b8a9c9') },
    glowColor: { value: new THREE.Color('#b8a9c9') },
    glowIntensity: { value: 0.5 },
    opacity: { value: 1.0 },
  },
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewPosition = -mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    uniform vec3 baseColor;
    uniform vec3 glowColor;
    uniform float glowIntensity;
    uniform float opacity;

    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vec3 viewDir = normalize(vViewPosition);

      // Ultra-soft fresnel for misty edges
      float fresnel = 1.0 - abs(dot(viewDir, vNormal));

      // Multiple falloff curves for nebula-like softness
      float softEdge = pow(fresnel, 1.5);
      float mistEdge = pow(fresnel, 0.8);
      float hazeEdge = pow(fresnel, 0.5);

      // Gaussian-like core fade
      float coreFade = exp(-fresnel * fresnel * 2.0);

      // Blend multiple soft layers
      float edgeGlow = softEdge * 0.4 + mistEdge * 0.3 + hazeEdge * 0.2;

      // Mix base color with glow - more glow at edges
      vec3 mistColor = mix(glowColor, vec3(0.7, 0.5, 0.9), hazeEdge * 0.3);
      vec3 finalColor = mix(baseColor * 0.7, mistColor, edgeGlow * glowIntensity);

      // Add inner luminosity
      finalColor += baseColor * coreFade * 0.3;

      // Ultra-soft alpha at edges - fade to mist
      float alpha = (coreFade * 0.7 + (1.0 - hazeEdge) * 0.3) * opacity;

      gl_FragColor = vec4(finalColor, alpha);
    }
  `,
};

// Ultra-soft, multi-layered atmospheric glow - nebula/mist style
function AtmosphericGlow({ color, intensity, hovered }: { color: string; intensity: number; hovered: boolean }) {
  const layers = useMemo(() => {
    const baseIntensity = hovered ? intensity * 1.8 : intensity;
    // More layers with gentler falloff for mist effect
    return [
      { scale: 1.08, opacity: 0.35 * baseIntensity },
      { scale: 1.18, opacity: 0.28 * baseIntensity },
      { scale: 1.32, opacity: 0.20 * baseIntensity },
      { scale: 1.5, opacity: 0.14 * baseIntensity },
      { scale: 1.75, opacity: 0.09 * baseIntensity },
      { scale: 2.1, opacity: 0.05 * baseIntensity },
      { scale: 2.6, opacity: 0.03 * baseIntensity },
      { scale: 3.2, opacity: 0.015 * baseIntensity },
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

// Soft planet sphere with fresnel edges
function SoftPlanetSphere({
  color,
  hovered,
  texture,
  onClick,
  onPointerOver,
  onPointerOut,
  sphereRef,
}: {
  color: string;
  hovered: boolean;
  texture: THREE.Texture | null;
  onClick: (e: any) => void;
  onPointerOver: (e: any) => void;
  onPointerOut: () => void;
  sphereRef: React.RefObject<THREE.Mesh>;
}) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // Update shader uniforms when color or hover state changes
  useFrame(() => {
    if (materialRef.current) {
      materialRef.current.uniforms.baseColor.value.set(color);
      materialRef.current.uniforms.glowColor.value.set(color);
      materialRef.current.uniforms.glowIntensity.value = hovered ? 1.2 : 0.7;
      materialRef.current.uniforms.opacity.value = hovered ? 0.95 : 0.85;
    }
  });

  // If we have a texture, use a hybrid approach
  if (texture) {
    return (
      <group>
        {/* Base textured sphere - slightly transparent */}
        <Sphere
          ref={sphereRef}
          args={[1, 64, 64]}
          onClick={onClick}
          onPointerOver={onPointerOver}
          onPointerOut={onPointerOut}
        >
          <meshBasicMaterial
            map={texture}
            transparent
            opacity={hovered ? 0.9 : 0.75}
          />
        </Sphere>
        {/* Soft glow overlay */}
        <Sphere args={[1.02, 64, 64]}>
          <shaderMaterial
            args={[SoftPlanetMaterial]}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </Sphere>
      </group>
    );
  }

  // No texture - use pure soft shader
  return (
    <Sphere
      ref={sphereRef}
      args={[1, 64, 64]}
      onClick={onClick}
      onPointerOver={onPointerOver}
      onPointerOut={onPointerOut}
    >
      <shaderMaterial
        ref={materialRef}
        args={[SoftPlanetMaterial]}
        transparent
        depthWrite={false}
      />
    </Sphere>
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

      {/* Soft planet sphere with fresnel edges */}
      <SoftPlanetSphere
        color={worldColor}
        hovered={hovered}
        texture={texture}
        onClick={handleClick}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        sphereRef={sphereRef}
      />

      {/* Inner core glow for extra luminosity */}
      <Sphere args={[0.85, 32, 32]}>
        <meshBasicMaterial
          color={worldColor}
          transparent
          opacity={hovered ? 0.4 : 0.25}
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

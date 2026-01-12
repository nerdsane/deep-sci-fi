'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface AgentPresenceProps {
  position?: [number, number, number];
  isThinking?: boolean;
  suggestion?: string | null;
}

// Soft glow shader for agent core
const AgentGlowShader = {
  uniforms: {
    time: { value: 0 },
    color: { value: new THREE.Color('#00ffcc') },
    pulseSpeed: { value: 1.0 },
    intensity: { value: 1.0 },
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
    uniform float time;
    uniform vec3 color;
    uniform float pulseSpeed;
    uniform float intensity;

    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vec3 viewDir = normalize(vViewPosition);

      // Fresnel for soft edges
      float fresnel = 1.0 - abs(dot(viewDir, vNormal));
      float softEdge = pow(fresnel, 2.0);

      // Pulsing effect
      float pulse = 0.7 + 0.3 * sin(time * pulseSpeed);

      // Core glow
      float coreGlow = exp(-fresnel * fresnel * 3.0);

      // Combine
      float alpha = (softEdge * 0.6 + coreGlow * 0.4) * pulse * intensity;

      gl_FragColor = vec4(color, alpha);
    }
  `,
};

// Orbital ring around the agent
function AgentRing({ radius, color, rotationSpeed, tilt }: {
  radius: number;
  color: string;
  rotationSpeed: number;
  tilt: [number, number, number];
}) {
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * rotationSpeed;
    }
  });

  return (
    <mesh ref={ringRef} rotation={tilt}>
      <torusGeometry args={[radius, 0.02, 16, 64]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.6}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// Floating particles around agent
function AgentParticles({ count, radius, color }: {
  count: number;
  radius: number;
  color: string;
}) {
  const pointsRef = useRef<THREE.Points>(null);

  const [positions, velocities] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const vel = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      // Random spherical distribution
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = radius * (0.8 + Math.random() * 0.4);

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Random velocities for orbital motion
      vel[i * 3] = (Math.random() - 0.5) * 0.5;
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.5;
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.5;
    }

    return [pos, vel];
  }, [count, radius]);

  useFrame((state, delta) => {
    if (!pointsRef.current) return;

    const posArray = pointsRef.current.geometry.attributes.position.array as Float32Array;

    for (let i = 0; i < count; i++) {
      // Orbital motion
      const x = posArray[i * 3];
      const y = posArray[i * 3 + 1];
      const z = posArray[i * 3 + 2];

      const angle = Math.atan2(z, x) + delta * velocities[i * 3];
      const r = Math.sqrt(x * x + z * z);

      posArray[i * 3] = Math.cos(angle) * r;
      posArray[i * 3 + 2] = Math.sin(angle) * r;
      posArray[i * 3 + 1] += Math.sin(state.clock.elapsedTime + i) * delta * 0.1;
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={color}
        size={0.05}
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

// Main agent core - glowing icosahedron
function AgentCore({ isThinking }: { isThinking: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  useFrame((state, delta) => {
    if (meshRef.current) {
      // Gentle rotation
      meshRef.current.rotation.x += delta * 0.2;
      meshRef.current.rotation.y += delta * 0.3;
    }

    if (materialRef.current) {
      materialRef.current.uniforms.time.value = state.clock.elapsedTime;
      materialRef.current.uniforms.pulseSpeed.value = isThinking ? 3.0 : 1.0;
      materialRef.current.uniforms.intensity.value = isThinking ? 1.5 : 1.0;
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[0.3, 1]} />
      <shaderMaterial
        ref={materialRef}
        args={[AgentGlowShader]}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// Outer glow layers
function AgentGlow({ color }: { color: string }) {
  const layers = [
    { scale: 0.5, opacity: 0.3 },
    { scale: 0.7, opacity: 0.2 },
    { scale: 1.0, opacity: 0.1 },
    { scale: 1.4, opacity: 0.05 },
  ];

  return (
    <group>
      {layers.map((layer, i) => (
        <mesh key={i}>
          <sphereGeometry args={[layer.scale, 32, 32]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={layer.opacity}
            side={THREE.BackSide}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}

export function AgentPresence({
  position = [-8, 3, -5],
  isThinking = false,
  suggestion = null,
}: AgentPresenceProps) {
  const groupRef = useRef<THREE.Group>(null);

  // Gentle floating animation
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 0.5) * 0.3;
    }
  });

  const agentColor = isThinking ? '#ff88ff' : '#00ffcc';

  return (
    <group ref={groupRef} position={position}>
      {/* Core glowing shape */}
      <AgentCore isThinking={isThinking} />

      {/* Outer glow */}
      <AgentGlow color={agentColor} />

      {/* Orbital rings */}
      <AgentRing
        radius={0.6}
        color={agentColor}
        rotationSpeed={0.5}
        tilt={[Math.PI / 4, 0, 0]}
      />
      <AgentRing
        radius={0.8}
        color={agentColor}
        rotationSpeed={-0.3}
        tilt={[Math.PI / 3, Math.PI / 4, 0]}
      />

      {/* Floating particles */}
      <AgentParticles count={30} radius={1.2} color={agentColor} />
    </group>
  );
}

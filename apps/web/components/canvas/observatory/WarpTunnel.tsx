'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface WarpTunnelProps {
  intensity: number; // 0-1, controls the effect strength
  active: boolean;
}

// Warp tunnel shader for hyperspace effect
const WarpTunnelShader = {
  uniforms: {
    time: { value: 0 },
    intensity: { value: 0 },
    color1: { value: new THREE.Color('#00ffcc') },
    color2: { value: new THREE.Color('#8844ff') },
  },
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vPosition;

    void main() {
      vUv = uv;
      vPosition = position;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform float time;
    uniform float intensity;
    uniform vec3 color1;
    uniform vec3 color2;

    varying vec2 vUv;
    varying vec3 vPosition;

    // Noise function for tunnel texture
    float noise(vec2 p) {
      return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
    }

    void main() {
      // Convert to polar coordinates from center
      vec2 center = vUv - 0.5;
      float dist = length(center);
      float angle = atan(center.y, center.x);

      // Tunnel effect - lines streaming toward center
      float tunnel = fract(dist * 8.0 - time * 3.0);
      tunnel = smoothstep(0.0, 0.1, tunnel) * smoothstep(1.0, 0.9, tunnel);

      // Radial streaks
      float streaks = sin(angle * 30.0 + time * 5.0) * 0.5 + 0.5;
      streaks = pow(streaks, 3.0);

      // Combine effects
      float effect = tunnel * 0.5 + streaks * 0.3;

      // Edge glow - stronger at edges
      float edgeGlow = smoothstep(0.3, 0.5, dist);

      // Color mixing
      vec3 tunnelColor = mix(color1, color2, sin(angle * 2.0 + time) * 0.5 + 0.5);

      // Final color with intensity control
      float alpha = (effect * edgeGlow + edgeGlow * 0.2) * intensity;

      // Add some sparkle
      float sparkle = noise(vUv * 100.0 + time * 10.0);
      sparkle = step(0.97, sparkle) * intensity;

      vec3 finalColor = tunnelColor + vec3(sparkle);

      gl_FragColor = vec4(finalColor, alpha * 0.7);
    }
  `,
};

// Streaking stars effect
function WarpStars({ intensity }: { intensity: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const [positions, velocities, sizes] = useMemo(() => {
    const count = 500;
    const pos = new Float32Array(count * 3);
    const vel = new Float32Array(count);
    const siz = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Stars distributed in a cylinder around the camera
      const angle = Math.random() * Math.PI * 2;
      const radius = 2 + Math.random() * 8;
      const z = (Math.random() - 0.5) * 40;

      pos[i * 3] = Math.cos(angle) * radius;
      pos[i * 3 + 1] = Math.sin(angle) * radius;
      pos[i * 3 + 2] = z;

      vel[i] = 0.5 + Math.random() * 1.5;
      siz[i] = 2 + Math.random() * 4;
    }

    return [pos, vel, siz];
  }, []);

  const starShader = useMemo(() => ({
    uniforms: {
      intensity: { value: 0 },
      time: { value: 0 },
    },
    vertexShader: `
      attribute float size;
      attribute float velocity;
      uniform float intensity;
      uniform float time;
      varying float vIntensity;

      void main() {
        vIntensity = intensity;

        // Stretch stars into lines based on intensity
        vec3 pos = position;

        // Move stars toward camera (negative Z)
        float z = mod(pos.z + time * velocity * 20.0 * intensity, 40.0) - 20.0;
        pos.z = z;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);

        // Size increases with intensity (streaking effect)
        float streakFactor = 1.0 + intensity * 10.0;
        gl_PointSize = size * streakFactor * (200.0 / -mvPosition.z);

        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      varying float vIntensity;

      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);

        // Stretch horizontally based on intensity for streak effect
        center.y *= 1.0 + vIntensity * 5.0;

        float dist = length(center);
        float alpha = 1.0 - smoothstep(0.0, 0.5, dist);

        // Brighter with intensity
        vec3 color = mix(vec3(0.8, 0.9, 1.0), vec3(0.5, 1.0, 0.9), vIntensity);

        gl_FragColor = vec4(color, alpha * (0.3 + vIntensity * 0.7));
      }
    `,
  }), []);

  useFrame((state, delta) => {
    if (!materialRef.current) return;

    materialRef.current.uniforms.intensity.value = intensity;
    materialRef.current.uniforms.time.value = state.clock.elapsedTime;
  });

  if (intensity < 0.01) return null;

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-velocity" args={[velocities, 1]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        args={[starShader]}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// Main tunnel cylinder effect
function TunnelCylinder({ intensity }: { intensity: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  useFrame((state) => {
    if (!materialRef.current) return;
    materialRef.current.uniforms.time.value = state.clock.elapsedTime;
    materialRef.current.uniforms.intensity.value = intensity;
  });

  if (intensity < 0.01) return null;

  return (
    <mesh ref={meshRef} rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[15, 15, 50, 64, 1, true]} />
      <shaderMaterial
        ref={materialRef}
        args={[WarpTunnelShader]}
        transparent
        side={THREE.BackSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// Central bright flash at destination
function DestinationFlash({ intensity }: { intensity: number }) {
  // Only show during arrive phase (intensity decreasing from 1)
  const flashIntensity = intensity > 0.5 ? 0 : (1 - intensity * 2);

  if (flashIntensity < 0.01) return null;

  return (
    <mesh position={[0, 0, -10]}>
      <planeGeometry args={[30, 30]} />
      <meshBasicMaterial
        color="#ffffff"
        transparent
        opacity={flashIntensity * 0.8}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  );
}

export function WarpTunnel({ intensity, active }: WarpTunnelProps) {
  if (!active && intensity < 0.01) return null;

  return (
    <group>
      {/* Streaking warp stars */}
      <WarpStars intensity={intensity} />

      {/* Tunnel cylinder effect */}
      <TunnelCylinder intensity={intensity} />

      {/* Destination flash */}
      <DestinationFlash intensity={intensity} />
    </group>
  );
}

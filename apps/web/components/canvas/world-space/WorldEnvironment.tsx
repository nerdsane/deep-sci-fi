/**
 * WorldEnvironment - Atmosphere and Background
 *
 * Creates the immersive atmosphere for the world space:
 * - Fog for depth
 * - Stars in background
 * - Ambient and directional lighting
 * - Optional HDRI environment from cover image
 */

'use client';

import { useMemo } from 'react';
import { Stars } from '@react-three/drei';
import type { WorldEnvironmentProps } from './types';

// Mood-based color palettes
const MOOD_COLORS = {
  dark: {
    fog: '#030303',
    ambient: 0.15,
    keyLight: '#8888aa',
    fillLight: '#004444',
  },
  mysterious: {
    fog: '#050510',
    ambient: 0.2,
    keyLight: '#9999bb',
    fillLight: '#003355',
  },
  hopeful: {
    fog: '#051015',
    ambient: 0.25,
    keyLight: '#aabbcc',
    fillLight: '#005566',
  },
  tense: {
    fog: '#080505',
    ambient: 0.15,
    keyLight: '#aa8877',
    fillLight: '#550022',
  },
  neutral: {
    fog: '#080808',
    ambient: 0.2,
    keyLight: '#ffffff',
    fillLight: '#006666',
  },
};

export function WorldEnvironment({
  mood = 'neutral',
}: WorldEnvironmentProps) {
  const colors = useMemo(() => MOOD_COLORS[mood] || MOOD_COLORS.neutral, [mood]);

  return (
    <>
      {/* Background color */}
      <color attach="background" args={[colors.fog]} />

      {/* Atmospheric fog - creates depth */}
      <fog attach="fog" args={[colors.fog, 15, 50]} />

      {/* Ambient light - base illumination */}
      <ambientLight intensity={colors.ambient} />

      {/* Key light - main directional light */}
      <directionalLight
        position={[10, 15, 5]}
        intensity={0.4}
        color={colors.keyLight}
        castShadow={false}
      />

      {/* Fill light - colored accent from opposite side */}
      <pointLight
        position={[-15, 5, -10]}
        intensity={0.3}
        color={colors.fillLight}
        distance={40}
      />

      {/* Rim light - subtle back lighting */}
      <pointLight
        position={[0, -5, -20]}
        intensity={0.15}
        color="#00ffcc"
        distance={30}
      />

      {/* Stars - background particle system */}
      <Stars
        radius={80}
        depth={60}
        count={1500}
        factor={3}
        saturation={0.2}
        fade
        speed={0.3}
      />

      {/* Ground reference plane (subtle grid) */}
      <gridHelper
        args={[100, 50, '#0a0a0a', '#050505']}
        position={[0, -5, 0]}
      />
    </>
  );
}

export default WorldEnvironment;

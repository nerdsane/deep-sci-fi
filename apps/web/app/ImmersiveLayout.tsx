'use client';

import { ShaderBackground, ProceduralAudioProvider, AudioControls } from '@/components/canvas/immersive';

export function ImmersiveLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProceduralAudioProvider defaultVolume={0.4}>
      {/* Procedural nebula background */}
      <ShaderBackground
        colorPrimary={[0.0, 0.35, 0.28]} // Teal (#00ffcc)
        colorSecondary={[0.15, 0.0, 0.3]} // Purple
        intensity={0.35}
      />

      {/* Main content */}
      {children}

      {/* Audio controls (bottom right) */}
      <AudioControls />
    </ProceduralAudioProvider>
  );
}

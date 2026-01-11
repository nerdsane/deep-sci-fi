'use client';

import { ProceduralAudioProvider, AudioControls } from '@/components/canvas/immersive';

export function ImmersiveLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProceduralAudioProvider defaultVolume={0.4}>
      {/* Main content */}
      {children}

      {/* Audio controls (bottom right) */}
      <AudioControls />
    </ProceduralAudioProvider>
  );
}

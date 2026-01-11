"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ============================================================================
// Types
// ============================================================================

export type UISoundType =
  | "hover"
  | "click"
  | "success"
  | "error"
  | "transition"
  | "notification";

export interface AudioSettings {
  masterVolume: number;
  isMuted: boolean;
  isEnabled: boolean;
}

// ============================================================================
// Procedural Sound Generators
// ============================================================================

function createHoverSound(ctx: AudioContext, volume: number) {
  const now = ctx.currentTime;

  // Soft high-pitched blip
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.type = "sine";
  osc.frequency.setValueAtTime(800, now);
  osc.frequency.exponentialRampToValueAtTime(1200, now + 0.05);

  gain.gain.setValueAtTime(0.05 * volume, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

  osc.start(now);
  osc.stop(now + 0.08);
}

function createClickSound(ctx: AudioContext, volume: number) {
  const now = ctx.currentTime;

  // Sharp click with slight resonance
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.type = "square";
  osc.frequency.setValueAtTime(400, now);
  osc.frequency.exponentialRampToValueAtTime(150, now + 0.05);

  gain.gain.setValueAtTime(0.08 * volume, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);

  osc.start(now);
  osc.stop(now + 0.06);
}

function createSuccessSound(ctx: AudioContext, volume: number) {
  const now = ctx.currentTime;

  // Ascending two-tone chime
  const osc1 = ctx.createOscillator();
  const osc2 = ctx.createOscillator();
  const gain = ctx.createGain();

  osc1.connect(gain);
  osc2.connect(gain);
  gain.connect(ctx.destination);

  osc1.type = "sine";
  osc1.frequency.setValueAtTime(523.25, now); // C5
  osc1.frequency.setValueAtTime(659.25, now + 0.1); // E5

  osc2.type = "sine";
  osc2.frequency.setValueAtTime(659.25, now + 0.1); // E5
  osc2.frequency.setValueAtTime(783.99, now + 0.2); // G5

  gain.gain.setValueAtTime(0.08 * volume, now);
  gain.gain.setValueAtTime(0.08 * volume, now + 0.1);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

  osc1.start(now);
  osc1.stop(now + 0.15);
  osc2.start(now + 0.1);
  osc2.stop(now + 0.35);
}

function createErrorSound(ctx: AudioContext, volume: number) {
  const now = ctx.currentTime;

  // Descending buzz
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.type = "sawtooth";
  osc.frequency.setValueAtTime(400, now);
  osc.frequency.exponentialRampToValueAtTime(150, now + 0.15);

  gain.gain.setValueAtTime(0.06 * volume, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

  osc.start(now);
  osc.stop(now + 0.2);
}

function createTransitionSound(ctx: AudioContext, volume: number) {
  const now = ctx.currentTime;

  // Whoosh (filtered noise)
  const bufferSize = ctx.sampleRate * 0.25;
  const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
  const data = buffer.getChannelData(0);

  for (let i = 0; i < bufferSize; i++) {
    data[i] = Math.random() * 2 - 1;
  }

  const noise = ctx.createBufferSource();
  noise.buffer = buffer;

  const filter = ctx.createBiquadFilter();
  filter.type = "bandpass";
  filter.frequency.setValueAtTime(2000, now);
  filter.frequency.exponentialRampToValueAtTime(400, now + 0.25);
  filter.Q.value = 2;

  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.04 * volume, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

  noise.connect(filter);
  filter.connect(gain);
  gain.connect(ctx.destination);

  noise.start(now);
  noise.stop(now + 0.25);
}

function createNotificationSound(ctx: AudioContext, volume: number) {
  const now = ctx.currentTime;

  // Gentle ping
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.type = "sine";
  osc.frequency.setValueAtTime(880, now); // A5
  osc.frequency.exponentialRampToValueAtTime(1320, now + 0.05);
  osc.frequency.setValueAtTime(1320, now + 0.1);

  gain.gain.setValueAtTime(0.06 * volume, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

  osc.start(now);
  osc.stop(now + 0.25);
}

// ============================================================================
// useProceduralAudio Hook
// ============================================================================

export function useProceduralAudio(defaultVolume = 0.5) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const [settings, setSettings] = useState<AudioSettings>({
    masterVolume: defaultVolume,
    isMuted: false,
    isEnabled: false,
  });

  // Initialize audio context on first user interaction
  const initialize = useCallback(() => {
    if (audioContextRef.current) return;

    audioContextRef.current = new AudioContext();
    setSettings((s) => ({ ...s, isEnabled: true }));
  }, []);

  // Ensure context is initialized and resumed
  const ensureContext = useCallback(async () => {
    if (!audioContextRef.current) {
      initialize();
    }

    if (audioContextRef.current?.state === "suspended") {
      await audioContextRef.current.resume();
    }

    return audioContextRef.current;
  }, [initialize]);

  // Play a procedural UI sound
  const playSound = useCallback(
    async (type: UISoundType) => {
      if (settings.isMuted) return;

      const ctx = await ensureContext();
      if (!ctx) return;

      const volume = settings.masterVolume;

      switch (type) {
        case "hover":
          createHoverSound(ctx, volume);
          break;
        case "click":
          createClickSound(ctx, volume);
          break;
        case "success":
          createSuccessSound(ctx, volume);
          break;
        case "error":
          createErrorSound(ctx, volume);
          break;
        case "transition":
          createTransitionSound(ctx, volume);
          break;
        case "notification":
          createNotificationSound(ctx, volume);
          break;
      }
    },
    [settings.isMuted, settings.masterVolume, ensureContext]
  );

  // Volume control
  const setVolume = useCallback((volume: number) => {
    setSettings((s) => ({
      ...s,
      masterVolume: Math.max(0, Math.min(1, volume)),
    }));
  }, []);

  // Mute toggle
  const toggleMute = useCallback(() => {
    setSettings((s) => ({ ...s, isMuted: !s.isMuted }));
  }, []);

  // Cleanup
  useEffect(() => {
    return () => {
      audioContextRef.current?.close();
    };
  }, []);

  return {
    playSound,
    setVolume,
    toggleMute,
    initialize,
    settings,
  };
}

// ============================================================================
// AudioContext Provider (for global audio state)
// ============================================================================

import { createContext, useContext, type ReactNode } from "react";

interface AudioContextType {
  playSound: (type: UISoundType) => Promise<void>;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  initialize: () => void;
  settings: AudioSettings;
}

const ProceduralAudioContext = createContext<AudioContextType | null>(null);

export function ProceduralAudioProvider({
  children,
  defaultVolume = 0.5,
}: {
  children: ReactNode;
  defaultVolume?: number;
}) {
  const audio = useProceduralAudio(defaultVolume);

  return (
    <ProceduralAudioContext.Provider value={audio}>
      {children}
    </ProceduralAudioContext.Provider>
  );
}

export function useAudio() {
  const context = useContext(ProceduralAudioContext);
  if (!context) {
    throw new Error("useAudio must be used within ProceduralAudioProvider");
  }
  return context;
}

// ============================================================================
// Audio Controls Component
// ============================================================================

export function AudioControls() {
  const { settings, setVolume, toggleMute, initialize } = useAudio();

  if (!settings.isEnabled) {
    return (
      <button
        type="button"
        onClick={initialize}
        className="fixed bottom-5 right-5 z-50 px-4 py-2 text-xs font-mono
                   bg-black/60 border border-cyan-500/30 rounded
                   text-cyan-400 hover:bg-cyan-500/10 hover:border-cyan-500/50
                   transition-all duration-200 backdrop-blur-sm"
      >
        Enable Audio
      </button>
    );
  }

  return (
    <div
      className="fixed bottom-5 right-5 z-50 flex items-center gap-2 px-3 py-2
                    bg-black/60 backdrop-blur-sm rounded-full border border-white/10"
    >
      <button
        type="button"
        onClick={toggleMute}
        className="text-sm hover:text-cyan-400 transition-colors"
      >
        {settings.isMuted ? "🔇" : settings.masterVolume > 0.5 ? "🔊" : "🔉"}
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.1}
        value={settings.isMuted ? 0 : settings.masterVolume}
        onChange={(e) => setVolume(parseFloat(e.target.value))}
        className="w-16 h-1 appearance-none bg-gray-700 rounded cursor-pointer
                   [&::-webkit-slider-thumb]:appearance-none
                   [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3
                   [&::-webkit-slider-thumb]:rounded-full
                   [&::-webkit-slider-thumb]:bg-cyan-400"
      />
    </div>
  );
}

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

const audioControlStyles = {
  container: {
    position: "fixed" as const,
    bottom: "20px",
    right: "360px", // Account for 340px chat sidebar + 20px margin
    zIndex: 50,
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 12px",
    background: "rgba(0, 0, 0, 0.7)",
    backdropFilter: "blur(8px)",
    border: "1px solid rgba(0, 255, 204, 0.2)",
  },
  enableButton: {
    position: "fixed" as const,
    bottom: "20px",
    right: "360px", // Account for 340px chat sidebar + 20px margin
    zIndex: 50,
    padding: "8px 16px",
    fontFamily: "var(--font-mono, monospace)",
    fontSize: "11px",
    fontWeight: 500,
    letterSpacing: "0.1em",
    textTransform: "uppercase" as const,
    color: "#00ffcc",
    background: "rgba(0, 0, 0, 0.7)",
    backdropFilter: "blur(8px)",
    border: "1px solid rgba(0, 255, 204, 0.3)",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  muteButton: {
    background: "transparent",
    border: "none",
    fontSize: "14px",
    cursor: "pointer",
    padding: "4px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "transform 0.15s ease",
  },
  slider: {
    width: "60px",
    height: "4px",
    appearance: "none" as const,
    WebkitAppearance: "none" as const,
    background: "rgba(255, 255, 255, 0.1)",
    cursor: "pointer",
    outline: "none",
  },
  volumeLabel: {
    fontFamily: "var(--font-mono, monospace)",
    fontSize: "10px",
    color: "rgba(0, 255, 204, 0.6)",
    minWidth: "24px",
    textAlign: "right" as const,
  },
};

// Minimalist SVG icons for audio controls
const SpeakerIcon = ({ muted, volume }: { muted: boolean; volume: number }) => {
  const bars = muted ? 0 : volume > 0.6 ? 3 : volume > 0.3 ? 2 : 1;
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 5.5h2l4-3v11l-4-3H2v-5z" fill={muted ? "none" : "currentColor"} />
      {!muted && bars >= 1 && <path d="M10 6c.5.5.8 1.2.8 2s-.3 1.5-.8 2" />}
      {!muted && bars >= 2 && <path d="M11.5 4.5c1 1 1.5 2.2 1.5 3.5s-.5 2.5-1.5 3.5" />}
      {!muted && bars >= 3 && <path d="M13 3c1.3 1.3 2 3 2 5s-.7 3.7-2 5" />}
      {muted && <path d="M10 5l5 6M15 5l-5 6" strokeLinecap="round" />}
    </svg>
  );
};

export function AudioControls() {
  const { settings, setVolume, toggleMute, initialize } = useAudio();
  const [isHovered, setIsHovered] = useState(false);

  if (!settings.isEnabled) {
    return (
      <button
        type="button"
        onClick={initialize}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{
          ...audioControlStyles.enableButton,
          background: isHovered ? "rgba(0, 255, 204, 0.1)" : "rgba(0, 0, 0, 0.7)",
          borderColor: isHovered ? "rgba(0, 255, 204, 0.5)" : "rgba(0, 255, 204, 0.3)",
          boxShadow: isHovered ? "0 0 15px rgba(0, 255, 204, 0.2)" : "none",
        }}
      >
        Audio
      </button>
    );
  }

  const volumePercent = Math.round(settings.masterVolume * 100);

  return (
    <div style={audioControlStyles.container}>
      <button
        type="button"
        onClick={toggleMute}
        style={{
          ...audioControlStyles.muteButton,
          color: settings.isMuted ? "rgba(255, 255, 255, 0.4)" : "#00ffcc",
        }}
        title={settings.isMuted ? "Unmute" : "Mute"}
      >
        <SpeakerIcon muted={settings.isMuted} volume={settings.masterVolume} />
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.1}
        value={settings.isMuted ? 0 : settings.masterVolume}
        onChange={(e) => setVolume(parseFloat(e.target.value))}
        style={audioControlStyles.slider}
        title={`Volume: ${volumePercent}%`}
      />
      <span style={audioControlStyles.volumeLabel}>{volumePercent}%</span>
      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 12px;
          height: 12px;
          background: #00ffcc;
          cursor: pointer;
        }
        input[type="range"]::-moz-range-thumb {
          width: 12px;
          height: 12px;
          background: #00ffcc;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}

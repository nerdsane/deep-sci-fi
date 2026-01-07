import { useState, useRef, useEffect, useCallback, createContext, useContext } from 'react';
import './music-manager.css';

interface MusicState {
  currentTrack: string | null;
  volume: number;
  isPlaying: boolean;
  isMuted: boolean;
}

interface MusicContextValue {
  state: MusicState;
  playTrack: (src: string, fadeIn?: boolean) => void;
  stopMusic: (fadeOut?: boolean) => void;
  pauseMusic: () => void;
  resumeMusic: () => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  crossfadeTo: (src: string, duration?: number) => void;
}

const MusicContext = createContext<MusicContextValue | null>(null);

export function useMusicManager() {
  const context = useContext(MusicContext);
  if (!context) {
    throw new Error('useMusicManager must be used within MusicProvider');
  }
  return context;
}

interface MusicProviderProps {
  children: React.ReactNode;
  defaultVolume?: number;
}

export function MusicProvider({ children, defaultVolume = 0.5 }: MusicProviderProps) {
  const [state, setState] = useState<MusicState>({
    currentTrack: null,
    volume: defaultVolume,
    isPlaying: false,
    isMuted: false,
  });

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const crossfadeAudioRef = useRef<HTMLAudioElement | null>(null);
  const fadeIntervalRef = useRef<number | null>(null);

  // Initialize audio element
  useEffect(() => {
    audioRef.current = new Audio();
    audioRef.current.loop = true;
    audioRef.current.volume = state.volume;

    crossfadeAudioRef.current = new Audio();
    crossfadeAudioRef.current.loop = true;

    return () => {
      audioRef.current?.pause();
      crossfadeAudioRef.current?.pause();
    };
  }, []);

  // Update volume when state changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = state.isMuted ? 0 : state.volume;
    }
  }, [state.volume, state.isMuted]);

  const clearFadeInterval = useCallback(() => {
    if (fadeIntervalRef.current) {
      clearInterval(fadeIntervalRef.current);
      fadeIntervalRef.current = null;
    }
  }, []);

  const playTrack = useCallback((src: string, fadeIn = true) => {
    if (!audioRef.current) return;

    clearFadeInterval();

    audioRef.current.src = src;
    audioRef.current.volume = fadeIn ? 0 : state.volume;

    audioRef.current.play().then(() => {
      setState(prev => ({
        ...prev,
        currentTrack: src,
        isPlaying: true,
      }));

      if (fadeIn) {
        let currentVolume = 0;
        const targetVolume = state.isMuted ? 0 : state.volume;
        const step = targetVolume / 20;

        fadeIntervalRef.current = window.setInterval(() => {
          currentVolume = Math.min(currentVolume + step, targetVolume);
          if (audioRef.current) {
            audioRef.current.volume = currentVolume;
          }

          if (currentVolume >= targetVolume) {
            clearFadeInterval();
          }
        }, 50);
      }
    }).catch(console.error);
  }, [state.volume, state.isMuted, clearFadeInterval]);

  const stopMusic = useCallback((fadeOut = true) => {
    if (!audioRef.current) return;

    clearFadeInterval();

    if (fadeOut && audioRef.current.volume > 0) {
      let currentVolume = audioRef.current.volume;
      const step = currentVolume / 20;

      fadeIntervalRef.current = window.setInterval(() => {
        currentVolume = Math.max(currentVolume - step, 0);
        if (audioRef.current) {
          audioRef.current.volume = currentVolume;
        }

        if (currentVolume <= 0) {
          audioRef.current?.pause();
          setState(prev => ({
            ...prev,
            currentTrack: null,
            isPlaying: false,
          }));
          clearFadeInterval();
        }
      }, 50);
    } else {
      audioRef.current.pause();
      setState(prev => ({
        ...prev,
        currentTrack: null,
        isPlaying: false,
      }));
    }
  }, [clearFadeInterval]);

  const pauseMusic = useCallback(() => {
    audioRef.current?.pause();
    setState(prev => ({ ...prev, isPlaying: false }));
  }, []);

  const resumeMusic = useCallback(() => {
    audioRef.current?.play().then(() => {
      setState(prev => ({ ...prev, isPlaying: true }));
    }).catch(console.error);
  }, []);

  const setVolume = useCallback((volume: number) => {
    setState(prev => ({ ...prev, volume, isMuted: false }));
  }, []);

  const toggleMute = useCallback(() => {
    setState(prev => ({ ...prev, isMuted: !prev.isMuted }));
  }, []);

  const crossfadeTo = useCallback((src: string, duration = 2000) => {
    if (!audioRef.current || !crossfadeAudioRef.current) return;

    const oldAudio = audioRef.current;
    const newAudio = crossfadeAudioRef.current;

    newAudio.src = src;
    newAudio.volume = 0;

    newAudio.play().then(() => {
      const startVolume = oldAudio.volume;
      const targetVolume = state.isMuted ? 0 : state.volume;
      const steps = duration / 50;
      let step = 0;

      fadeIntervalRef.current = window.setInterval(() => {
        step++;
        const progress = step / steps;

        oldAudio.volume = startVolume * (1 - progress);
        newAudio.volume = targetVolume * progress;

        if (step >= steps) {
          oldAudio.pause();
          clearFadeInterval();

          // Swap references
          const temp = audioRef.current;
          audioRef.current = crossfadeAudioRef.current;
          crossfadeAudioRef.current = temp;

          setState(prev => ({
            ...prev,
            currentTrack: src,
            isPlaying: true,
          }));
        }
      }, 50);
    }).catch(console.error);
  }, [state.volume, state.isMuted, clearFadeInterval]);

  const value: MusicContextValue = {
    state,
    playTrack,
    stopMusic,
    pauseMusic,
    resumeMusic,
    setVolume,
    toggleMute,
    crossfadeTo,
  };

  return (
    <MusicContext.Provider value={value}>
      {children}
    </MusicContext.Provider>
  );
}

// Minimal UI control for background music
interface MusicControlProps {
  className?: string;
}

export function MusicControl({ className }: MusicControlProps) {
  const { state, pauseMusic, resumeMusic, toggleMute, setVolume } = useMusicManager();

  if (!state.currentTrack) return null;

  return (
    <div className={`music-control ${className || ''}`}>
      <button
        className="music-control__btn"
        onClick={state.isPlaying ? pauseMusic : resumeMusic}
        title={state.isPlaying ? 'Pause music' : 'Play music'}
      >
        {state.isPlaying ? '⏸' : '▶'}
      </button>
      <button
        className="music-control__btn"
        onClick={toggleMute}
        title={state.isMuted ? 'Unmute' : 'Mute'}
      >
        {state.isMuted ? '🔇' : '🔊'}
      </button>
      <input
        type="range"
        className="music-control__volume"
        min={0}
        max={1}
        step={0.1}
        value={state.isMuted ? 0 : state.volume}
        onChange={(e) => setVolume(parseFloat(e.target.value))}
        title="Volume"
      />
    </div>
  );
}

export default MusicProvider;

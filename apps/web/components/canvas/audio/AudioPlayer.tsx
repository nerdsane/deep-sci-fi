import { useState, useRef, useEffect, useCallback } from 'react';
import './audio-player.css';

interface AudioPlayerProps {
  src: string;
  title?: string;
  artist?: string;
  autoPlay?: boolean;
  loop?: boolean;
  showWaveform?: boolean;
  minimal?: boolean;
  onEnded?: () => void;
  onTimeUpdate?: (currentTime: number, duration: number) => void;
}

export function AudioPlayer({
  src,
  title,
  artist,
  autoPlay = false,
  loop = false,
  showWaveform = false,
  minimal = false,
  onEnded,
  onTimeUpdate,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      onTimeUpdate?.(audio.currentTime, audio.duration);
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      onEnded?.();
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [onEnded, onTimeUpdate]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const time = parseFloat(e.target.value);
    audio.currentTime = time;
    setCurrentTime(time);
  }, []);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    setIsMuted(false);
  }, []);

  const toggleMute = useCallback(() => {
    setIsMuted(!isMuted);
  }, [isMuted]);

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  if (minimal) {
    return (
      <div className="audio-player audio-player--minimal">
        <audio ref={audioRef} src={src} autoPlay={autoPlay} loop={loop} />
        <button className="audio-player__play-btn" onClick={togglePlay}>
          {isPlaying ? '⏸' : '▶'}
        </button>
        <div className="audio-player__time">{formatTime(currentTime)}</div>
      </div>
    );
  }

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={src} autoPlay={autoPlay} loop={loop} />

      {/* Track Info */}
      {(title || artist) && (
        <div className="audio-player__info">
          {title && <span className="audio-player__title">{title}</span>}
          {artist && <span className="audio-player__artist">{artist}</span>}
        </div>
      )}

      {/* Controls */}
      <div className="audio-player__controls">
        <button className="audio-player__play-btn" onClick={togglePlay}>
          {isPlaying ? '⏸' : '▶'}
        </button>

        {/* Progress */}
        <div className="audio-player__progress">
          <span className="audio-player__time">{formatTime(currentTime)}</span>
          <input
            type="range"
            className="audio-player__seek"
            min={0}
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
          />
          <span className="audio-player__time">{formatTime(duration)}</span>
        </div>

        {/* Volume */}
        <div className="audio-player__volume">
          <button className="audio-player__mute-btn" onClick={toggleMute}>
            {isMuted || volume === 0 ? '🔇' : volume < 0.5 ? '🔈' : '🔊'}
          </button>
          <input
            type="range"
            className="audio-player__volume-slider"
            min={0}
            max={1}
            step={0.1}
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
          />
        </div>
      </div>

      {/* Waveform placeholder */}
      {showWaveform && (
        <div className="audio-player__waveform">
          <div
            className="audio-player__waveform-progress"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}

export default AudioPlayer;

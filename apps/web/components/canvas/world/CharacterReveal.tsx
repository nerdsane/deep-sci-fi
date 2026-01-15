/**
 * CharacterReveal - Silhouettes → dramatic reveals
 *
 * Features:
 * - Initial silhouette state
 * - Dramatic reveal animation
 * - Character portrait and details
 * - Attribute display
 * - Optional voiceline playback
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import type { CharacterRevealProps } from './types';

export function CharacterReveal({
  characterId,
  name,
  title,
  description,
  imageUrl,
  silhouetteOnly = false,
  revealed: externalRevealed,
  attributes = [],
  quote,
  voicelineUrl,
  revealAnimation = 'dramatic',
  revealDelay = 0,
  onReveal,
  onClick,
  style,
}: CharacterRevealProps) {
  const [internalRevealed, setInternalRevealed] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);

  const revealed = externalRevealed !== undefined ? externalRevealed : internalRevealed;

  // Auto-reveal with delay
  useEffect(() => {
    if (revealDelay > 0 && !silhouetteOnly && !revealed) {
      const timer = setTimeout(() => {
        handleReveal();
      }, revealDelay);
      return () => clearTimeout(timer);
    }
  }, [revealDelay, silhouetteOnly, revealed]);

  const handleReveal = useCallback(() => {
    if (revealed) return;
    setIsAnimating(true);
    setInternalRevealed(true);

    if (onReveal) {
      onReveal();
    }

    // Play voiceline if available
    if (voicelineUrl) {
      const audio = new Audio(voicelineUrl);
      audio.play().catch(console.error);
      setAudioPlaying(true);
      audio.onended = () => setAudioPlaying(false);
    }

    // End animation
    setTimeout(() => setIsAnimating(false), 1000);
  }, [revealed, voicelineUrl, onReveal]);

  const handleClick = useCallback(() => {
    if (!revealed && !silhouetteOnly) {
      handleReveal();
    }
    if (onClick) {
      onClick();
    }
  }, [revealed, silhouetteOnly, handleReveal, onClick]);

  const getAnimationClass = () => {
    if (!isAnimating) return '';
    switch (revealAnimation) {
      case 'fade':
        return 'reveal-fade';
      case 'slide':
        return 'reveal-slide';
      case 'dramatic':
        return 'reveal-dramatic';
      default:
        return '';
    }
  };

  const groupedAttributes = attributes.reduce((acc, attr) => {
    const cat = attr.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(attr);
    return acc;
  }, {} as Record<string, typeof attributes>);

  return (
    <div
      className={`character-reveal ${getAnimationClass()}`}
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: '500px',
        background: 'rgba(10, 10, 10, 0.95)',
        border: `1px solid ${revealed ? 'rgba(0, 255, 204, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
        borderRadius: '8px',
        overflow: 'hidden',
        cursor: !revealed && !silhouetteOnly ? 'pointer' : 'default',
        transition: 'border-color 0.3s ease',
        ...style,
      }}
      onClick={handleClick}
    >
      {/* Character Portrait */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '300px',
          background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.9))',
          overflow: 'hidden',
        }}
      >
        {imageUrl && (
          <img
            src={imageUrl}
            alt={name}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              filter: !revealed || silhouetteOnly ? 'brightness(0) contrast(200%)' : 'none',
              transition: 'filter 0.8s ease',
            }}
          />
        )}

        {/* Silhouette overlay */}
        {(!revealed || silhouetteOnly) && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '4rem',
            }}
          >
            👤
          </div>
        )}

        {/* Reveal hint */}
        {!revealed && !silhouetteOnly && (
          <div
            style={{
              position: 'absolute',
              bottom: '1rem',
              left: '50%',
              transform: 'translateX(-50%)',
              padding: '0.5rem 1rem',
              background: 'rgba(0, 255, 204, 0.2)',
              border: '1px solid rgba(0, 255, 204, 0.5)',
              borderRadius: '20px',
              color: 'var(--color-teal, #00ffcc)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              animation: 'pulse 2s ease-in-out infinite',
            }}
          >
            Click to Reveal
          </div>
        )}

        {/* Audio indicator */}
        {audioPlaying && (
          <div
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              padding: '0.5rem',
              background: 'rgba(0, 255, 204, 0.2)',
              borderRadius: '50%',
              animation: 'pulse 1s ease-in-out infinite',
            }}
          >
            🔊
          </div>
        )}
      </div>

      {/* Character Info */}
      <div style={{ padding: '1.5rem' }}>
        {/* Name and Title */}
        <div style={{ marginBottom: '1rem' }}>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '1.5rem',
              color: revealed ? 'var(--color-teal, #00ffcc)' : 'var(--color-text-tertiary, #5a5a5a)',
              marginBottom: '0.25rem',
              filter: !revealed && !silhouetteOnly ? 'blur(4px)' : 'none',
              transition: 'all 0.5s ease',
            }}
          >
            {revealed || !silhouetteOnly ? name : '???'}
          </div>
          {title && revealed && (
            <div
              style={{
                fontSize: '0.9rem',
                color: 'var(--color-text-secondary, #8a8a8a)',
                fontStyle: 'italic',
              }}
            >
              {title}
            </div>
          )}
        </div>

        {/* Description */}
        {revealed && (
          <div
            style={{
              fontSize: '0.9rem',
              color: 'var(--color-text-secondary, #8a8a8a)',
              lineHeight: 1.7,
              marginBottom: '1rem',
              fontFamily: 'var(--font-sans)',
            }}
          >
            {description}
          </div>
        )}

        {/* Quote */}
        {quote && revealed && (
          <div
            style={{
              padding: '1rem',
              background: 'rgba(0, 255, 204, 0.05)',
              borderLeft: '3px solid var(--color-teal, #00ffcc)',
              marginBottom: '1rem',
              fontStyle: 'italic',
              color: 'var(--color-text-primary, #c8c8c8)',
              fontSize: '0.9rem',
            }}
          >
            "{quote}"
          </div>
        )}

        {/* Attributes */}
        {revealed && Object.keys(groupedAttributes).length > 0 && (
          <div style={{ marginTop: '1.5rem' }}>
            {Object.entries(groupedAttributes).map(([category, attrs]) => (
              <div key={category} style={{ marginBottom: '1rem' }}>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-tertiary, #5a5a5a)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    marginBottom: '0.5rem',
                  }}
                >
                  {category}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {attrs.map((attr, index) => (
                    <div
                      key={index}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 0.75rem',
                        background: 'rgba(0, 0, 0, 0.3)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '4px',
                        fontSize: '0.85rem',
                      }}
                    >
                      {attr.icon && <span>{attr.icon}</span>}
                      <span style={{ color: 'var(--color-text-secondary, #8a8a8a)' }}>{attr.label}:</span>
                      <span style={{ color: 'var(--color-text-primary, #c8c8c8)', fontWeight: 500 }}>
                        {attr.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes pulse {
          0%,
          100% {
            opacity: 0.8;
            transform: translateX(-50%) scale(1);
          }
          50% {
            opacity: 1;
            transform: translateX(-50%) scale(1.05);
          }
        }

        .reveal-fade {
          animation: fadeIn 0.8s ease-out;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        .reveal-slide {
          animation: slideUp 0.6s ease-out;
        }

        @keyframes slideUp {
          from {
            transform: translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }

        .reveal-dramatic {
          animation: dramaticReveal 1s ease-out;
        }

        @keyframes dramaticReveal {
          0% {
            transform: scale(0.95);
            opacity: 0;
          }
          50% {
            transform: scale(1.02);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}

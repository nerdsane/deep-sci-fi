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
import './character-reveal.css';

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
  locked = false,
  discovered = true,
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
    if (revealed || locked) return;
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
    setTimeout(() => setIsAnimating(false), 1500);
  }, [revealed, locked, voicelineUrl, onReveal]);

  const handleClick = useCallback(() => {
    if (!revealed && !silhouetteOnly && !locked) {
      handleReveal();
    }
    if (onClick) {
      onClick();
    }
  }, [revealed, silhouetteOnly, locked, handleReveal, onClick]);

  return (
    <div
      className={`character-reveal ${revealed ? 'character-reveal--revealed' : ''} ${locked ? 'character-reveal--locked' : ''}`}
      style={style}
      onClick={handleClick}
    >
      {/* Character Visual */}
      <div className="character-reveal__visual">
        {!revealed ? (
          <div className={`character-reveal__silhouette ${!revealed ? 'character-reveal__silhouette--unrevealed' : ''}`}>
            👤
          </div>
        ) : imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className={`character-reveal__image ${revealed ? 'character-reveal__image--revealed' : ''} ${isAnimating ? `character-reveal__visual--${revealAnimation}` : ''}`}
          />
        ) : (
          <div className="character-reveal__silhouette">
            👤
          </div>
        )}

        {/* Reveal effect overlay */}
        {isAnimating && (
          <div className="character-reveal__overlay character-reveal__overlay--revealing" />
        )}
      </div>

      {/* Character Info */}
      <div className="character-reveal__info">
        <div className={`character-reveal__name ${!revealed ? 'character-reveal__name--unrevealed' : ''}`}>
          {revealed ? name : '???'}
        </div>

        {title && revealed && (
          <div className="character-reveal__title">{title}</div>
        )}

        <div className={`character-reveal__description ${!revealed ? 'character-reveal__description--unrevealed' : ''}`}>
          {revealed ? description : 'Unknown character'}
        </div>

        {/* Status badge */}
        <div className={`character-reveal__status ${!revealed ? 'character-reveal__status--unrevealed' : ''}`}>
          {revealed ? 'Revealed' : 'Hidden'}
        </div>

        {/* Attributes (if revealed) */}
        {revealed && attributes.length > 0 && (
          <div className="character-reveal__attributes">
            {attributes.map((attr, index) => (
              <div key={index} className="character-reveal__attribute">
                <span className="character-reveal__attribute-name">{attr.name}:</span>
                <span className="character-reveal__attribute-value">{attr.value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Quote (if revealed) */}
        {revealed && quote && (
          <div className="character-reveal__quote">
            "{quote}"
          </div>
        )}

        {/* Reveal prompt */}
        {!revealed && !silhouetteOnly && !locked && (
          <div className="character-reveal__prompt">
            Click to reveal →
          </div>
        )}

        {/* Locked message */}
        {locked && (
          <div className="character-reveal__locked-message">
            🔒 Locked
          </div>
        )}
      </div>
    </div>
  );
}

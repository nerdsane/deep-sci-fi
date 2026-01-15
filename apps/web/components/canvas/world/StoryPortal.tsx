/**
 * StoryPortal - Visual gateways to narratives
 *
 * Features:
 * - Gateway/portal visual with glow effects
 * - Story preview information
 * - Progress tracking
 * - Badges for story state (new, continued, branch, complete)
 * - Animated glow and entrance effects
 */

'use client';

import { useState, useCallback } from 'react';
import type { StoryPortalProps } from './types';
import './story-portal.css';

export function StoryPortal({
  portalId,
  storyId,
  title,
  subtitle,
  description,
  imageUrl,
  worldId,
  badges = [],
  locked = false,
  progress = 0,
  segmentCount,
  lastAccessedAt,
  portalType = 'gateway',
  glowColor = '#00ffcc',
  animated = true,
  onEnter,
  onClick,
  style,
}: StoryPortalProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = useCallback(() => {
    if (locked) return;
    if (onEnter) {
      onEnter();
    }
    if (onClick) {
      onClick();
    }
  }, [locked, onEnter, onClick]);

  const getPortalIcon = () => {
    const icons: Record<string, string> = {
      gateway: '🚪',
      door: '🚪',
      rift: '🌀',
      entrance: '⛩️',
    };
    return icons[portalType] || '🚪';
  };

  const formatLastAccessed = (timestamp?: string) => {
    if (!timestamp) return null;
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div
      className={`story-portal story-portal--${portalType} ${locked ? 'story-portal--locked' : ''} ${animated ? 'animated' : ''}`}
      style={style}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Portal Visual */}
      <div
        className={`story-portal__visual ${!imageUrl ? 'story-portal__visual--no-image' : ''}`}
        style={imageUrl ? { backgroundImage: `linear-gradient(180deg, rgba(0, 0, 0, 0.3), rgba(10, 10, 10, 0.95)), url(${imageUrl})` } : undefined}
      >
        {/* Glow effect */}
        <div className={`story-portal__glow ${animated ? 'story-portal__glow--animated' : ''}`} style={{ background: `radial-gradient(circle at center, ${glowColor}33, transparent 70%)` }} />

        {/* Portal icon */}
        <div className={`story-portal__icon ${animated ? 'story-portal__icon--animated' : ''}`} style={{ filter: `drop-shadow(0 0 20px ${glowColor})` }}>
          {locked ? '🔒' : getPortalIcon()}
        </div>

        {/* Badges */}
        {badges.length > 0 && (
          <div className="story-portal__badges">
            {badges.map((badge, index) => (
              <div key={index} className={`story-portal__badge story-portal__badge--${badge.variant || 'new'}`} style={badge.color ? { background: `${badge.color}33`, borderColor: badge.color, color: badge.color } : undefined}>
                {badge.label}
              </div>
            ))}
          </div>
        )}

        {/* Progress bar */}
        {progress > 0 && progress < 100 && (
          <div className="story-portal__progress-track">
            <div className="story-portal__progress-bar" style={{ width: `${progress}%`, background: glowColor, boxShadow: `0 0 10px ${glowColor}` }} />
          </div>
        )}
      </div>

      {/* Story Info */}
      <div className="story-portal__info">
        <div className={`story-portal__title ${locked ? 'story-portal--locked' : ''}`} style={!locked ? { color: glowColor } : undefined}>{title}</div>

        {subtitle && <div className="story-portal__subtitle">{subtitle}</div>}

        {description && <div className="story-portal__description">{description}</div>}

        {/* Metadata */}
        <div className="story-portal__metadata">
          {segmentCount !== undefined && (
            <div>
              <span className="story-portal__meta-label">Segments:</span> {segmentCount}
            </div>
          )}
          {progress > 0 && (
            <div>
              <span className="story-portal__meta-label">Progress:</span> {Math.round(progress)}%
            </div>
          )}
          {lastAccessedAt && (
            <div>
              <span className="story-portal__meta-label">Last:</span> {formatLastAccessed(lastAccessedAt)}
            </div>
          )}
        </div>

        {/* Enter prompt */}
        {!locked && isHovered && (
          <div className="story-portal__enter-prompt" style={{ color: glowColor, background: `${glowColor}11`, borderColor: `${glowColor}33` }}>
            Enter Story →
          </div>
        )}

        {/* Locked message */}
        {locked && (
          <div className="story-portal__locked-message">
            🔒 Locked
          </div>
        )}
      </div>
    </div>
  );
}

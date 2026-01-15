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

  const getBadgeColor = (variant?: string) => {
    const colors: Record<string, string> = {
      new: '#00ffcc',
      continued: '#00ffff',
      branch: '#ff8800',
      complete: '#88ff00',
    };
    return variant ? colors[variant] || '#00ffcc' : '#00ffcc';
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
      className={`story-portal ${animated ? 'animated' : ''}`}
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: '400px',
        background: 'rgba(10, 10, 10, 0.95)',
        border: `1px solid ${locked ? 'rgba(255, 255, 255, 0.1)' : glowColor + '33'}`,
        borderRadius: '12px',
        overflow: 'hidden',
        cursor: locked ? 'not-allowed' : 'pointer',
        transition: 'all 0.3s ease',
        transform: isHovered && !locked ? 'scale(1.02)' : 'scale(1)',
        filter: locked ? 'grayscale(100%)' : 'none',
        ...style,
      }}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Portal Visual */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '200px',
          background: imageUrl
            ? `linear-gradient(180deg, rgba(0, 0, 0, 0.3), rgba(10, 10, 10, 0.95)), url(${imageUrl})`
            : `radial-gradient(circle at center, ${glowColor}22, transparent)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {/* Glow effect */}
        <div
          className={animated ? 'portal-glow' : ''}
          style={{
            position: 'absolute',
            inset: 0,
            background: `radial-gradient(circle at center, ${glowColor}33, transparent 70%)`,
            opacity: isHovered ? 1 : 0.6,
            transition: 'opacity 0.3s ease',
          }}
        />

        {/* Portal icon */}
        <div
          style={{
            fontSize: '4rem',
            filter: `drop-shadow(0 0 20px ${glowColor})`,
            animation: animated ? 'float 3s ease-in-out infinite' : 'none',
          }}
        >
          {locked ? '🔒' : getPortalIcon()}
        </div>

        {/* Badges */}
        {badges.length > 0 && (
          <div
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
              alignItems: 'flex-end',
            }}
          >
            {badges.map((badge, index) => (
              <div
                key={index}
                style={{
                  padding: '0.25rem 0.75rem',
                  background: badge.color || getBadgeColor(badge.variant) + '33',
                  border: `1px solid ${badge.color || getBadgeColor(badge.variant)}`,
                  borderRadius: '12px',
                  color: badge.color || getBadgeColor(badge.variant),
                  fontSize: '0.7rem',
                  fontFamily: 'var(--font-mono)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                {badge.label}
              </div>
            ))}
          </div>
        )}

        {/* Progress bar */}
        {progress > 0 && progress < 100 && (
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '4px',
              background: 'rgba(0, 0, 0, 0.5)',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progress}%`,
                background: glowColor,
                transition: 'width 0.3s ease',
                boxShadow: `0 0 10px ${glowColor}`,
              }}
            />
          </div>
        )}
      </div>

      {/* Story Info */}
      <div style={{ padding: '1.5rem' }}>
        {/* Title */}
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.3rem',
            color: locked ? 'var(--color-text-tertiary, #5a5a5a)' : glowColor,
            marginBottom: '0.5rem',
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>

        {/* Subtitle */}
        {subtitle && (
          <div
            style={{
              fontSize: '0.9rem',
              color: 'var(--color-text-secondary, #8a8a8a)',
              marginBottom: '0.75rem',
              fontStyle: 'italic',
            }}
          >
            {subtitle}
          </div>
        )}

        {/* Description */}
        {description && (
          <div
            style={{
              fontSize: '0.85rem',
              color: 'var(--color-text-secondary, #8a8a8a)',
              lineHeight: 1.6,
              marginBottom: '1rem',
              fontFamily: 'var(--font-sans)',
            }}
          >
            {description}
          </div>
        )}

        {/* Metadata */}
        <div
          style={{
            display: 'flex',
            gap: '1rem',
            fontSize: '0.75rem',
            color: 'var(--color-text-tertiary, #5a5a5a)',
            fontFamily: 'var(--font-mono)',
            paddingTop: '1rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          }}
        >
          {segmentCount !== undefined && (
            <div>
              <span style={{ opacity: 0.6 }}>Segments:</span> {segmentCount}
            </div>
          )}
          {progress > 0 && (
            <div>
              <span style={{ opacity: 0.6 }}>Progress:</span> {Math.round(progress)}%
            </div>
          )}
          {lastAccessedAt && (
            <div>
              <span style={{ opacity: 0.6 }}>Last:</span> {formatLastAccessed(lastAccessedAt)}
            </div>
          )}
        </div>

        {/* Enter prompt */}
        {!locked && isHovered && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: glowColor + '11',
              border: `1px solid ${glowColor}33`,
              borderRadius: '6px',
              textAlign: 'center',
              color: glowColor,
              fontSize: '0.85rem',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}
          >
            Enter Story →
          </div>
        )}

        {/* Locked message */}
        {locked && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              textAlign: 'center',
              color: 'var(--color-text-tertiary, #5a5a5a)',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)',
            }}
          >
            🔒 Locked
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes float {
          0%,
          100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-10px);
          }
        }

        .animated .portal-glow {
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%,
          100% {
            opacity: 0.6;
          }
          50% {
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}

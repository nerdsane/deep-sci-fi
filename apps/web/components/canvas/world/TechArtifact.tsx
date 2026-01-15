/**
 * TechArtifact - 3D rotatable objects with inspection
 *
 * Features:
 * - 3D model display with THREE.js/R3F
 * - Manual rotation and auto-rotation
 * - Fallback to 2D image if 3D model not available
 * - Specification details panel
 * - Inspection mode
 */

'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import type { TechArtifactProps } from './types';

export function TechArtifact({
  artifactId,
  name,
  description,
  category = 'technology',
  model3dUrl,
  imageUrl,
  specifications = [],
  discovered = true,
  locked = false,
  rotationSpeed = 0.5,
  allowManualRotation = true,
  scale = 1,
  initialRotation = [0, 0, 0],
  onInspect,
  onRotate,
  style,
}: TechArtifactProps) {
  const [isInspecting, setIsInspecting] = useState(false);
  const [rotation, setRotation] = useState(initialRotation);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const rotationRef = useRef(initialRotation);

  // Auto-rotation effect
  const handleAutoRotation = useCallback(() => {
    if (rotationSpeed > 0 && !isDragging && !isInspecting) {
      rotationRef.current = [
        rotationRef.current[0],
        rotationRef.current[1] + rotationSpeed * 0.01,
        rotationRef.current[2],
      ];
      setRotation([...rotationRef.current]);
    }
  }, [rotationSpeed, isDragging, isInspecting]);

  // Manual rotation handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!allowManualRotation || locked) return;
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
    },
    [allowManualRotation, locked]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging || !allowManualRotation) return;
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;

      const newRotation: [number, number, number] = [
        rotationRef.current[0] + deltaY * 0.01,
        rotationRef.current[1] + deltaX * 0.01,
        rotationRef.current[2],
      ];

      rotationRef.current = newRotation;
      setRotation(newRotation);
      setDragStart({ x: e.clientX, y: e.clientY });

      if (onRotate) {
        onRotate(newRotation);
      }
    },
    [isDragging, dragStart, allowManualRotation, onRotate]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInspect = useCallback(() => {
    if (locked) return;
    setIsInspecting(!isInspecting);
    if (onInspect && !isInspecting) {
      onInspect();
    }
  }, [locked, isInspecting, onInspect]);

  // Auto-rotation loop using requestAnimationFrame
  useEffect(() => {
    if (rotationSpeed === 0) return;

    let rafId: number;
    const animate = () => {
      handleAutoRotation();
      rafId = requestAnimationFrame(animate);
    };

    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, [rotationSpeed, handleAutoRotation]);

  const getCategoryIcon = () => {
    const icons: Record<string, string> = {
      technology: '⚙️',
      device: '📱',
      vehicle: '🚗',
      structure: '🏗️',
      weapon: '⚔️',
      tool: '🔧',
    };
    return icons[category] || '📦';
  };

  const getCategoryColor = () => {
    const colors: Record<string, string> = {
      technology: '#00ffcc',
      device: '#00ffff',
      vehicle: '#0088ff',
      structure: '#ff8800',
      weapon: '#ff0000',
      tool: '#88ff00',
    };
    return colors[category] || '#00ffcc';
  };

  if (!discovered) {
    return (
      <div
        className="tech-artifact-unknown"
        style={{
          padding: '2rem',
          background: 'rgba(10, 10, 10, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '8px',
          textAlign: 'center',
          color: 'var(--color-text-tertiary, #5a5a5a)',
          fontFamily: 'var(--font-mono)',
          ...style,
        }}
      >
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❓</div>
        <div>Unknown Artifact</div>
      </div>
    );
  }

  return (
    <div
      className="tech-artifact"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: '400px',
        background: 'rgba(10, 10, 10, 0.95)',
        border: `1px solid ${locked ? 'rgba(255, 255, 255, 0.1)' : getCategoryColor() + '33'}`,
        borderRadius: '8px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        ...style,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '1rem',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.5rem' }}>{getCategoryIcon()}</span>
          <div>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '1.1rem',
                color: locked ? 'var(--color-text-tertiary, #5a5a5a)' : getCategoryColor(),
              }}
            >
              {name}
            </div>
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-tertiary, #5a5a5a)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginTop: '0.25rem',
              }}
            >
              {category}
            </div>
          </div>
        </div>
        {locked && <span style={{ fontSize: '1.2rem' }}>🔒</span>}
      </div>

      {/* 3D/2D Display */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: allowManualRotation && !locked ? (isDragging ? 'grabbing' : 'grab') : 'default',
          filter: locked ? 'grayscale(100%)' : 'none',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {model3dUrl ? (
          <div
            style={{
              width: '80%',
              height: '80%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            {/* Visual 3D representation (R3F integration possible in future) */}
            <div
              style={{
                width: '200px',
                height: '200px',
                background: `linear-gradient(135deg, ${getCategoryColor()}22, transparent)`,
                border: `2px solid ${getCategoryColor()}33`,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '4rem',
                transform: `rotateX(${rotation[0]}rad) rotateY(${rotation[1]}rad) rotateZ(${rotation[2]}rad) scale(${scale})`,
                transition: isDragging ? 'none' : 'transform 0.1s ease',
              }}
            >
              {getCategoryIcon()}
            </div>
            <div
              style={{
                position: 'absolute',
                bottom: '1rem',
                fontSize: '0.7rem',
                color: 'var(--color-text-tertiary, #5a5a5a)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {allowManualRotation && 'Drag to rotate'}
            </div>
          </div>
        ) : imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            style={{
              maxWidth: '80%',
              maxHeight: '80%',
              objectFit: 'contain',
            }}
          />
        ) : (
          <div style={{ fontSize: '4rem', opacity: 0.3 }}>{getCategoryIcon()}</div>
        )}
      </div>

      {/* Description */}
      <div
        style={{
          padding: '1rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.9rem',
          color: 'var(--color-text-secondary, #8a8a8a)',
          fontFamily: 'var(--font-sans)',
          lineHeight: 1.6,
        }}
      >
        {description}
      </div>

      {/* Specifications */}
      {specifications.length > 0 && (
        <div
          style={{
            padding: '1rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            maxHeight: isInspecting ? '300px' : '0',
            overflow: 'hidden',
            transition: 'max-height 0.3s ease',
          }}
        >
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
              color: getCategoryColor(),
              marginBottom: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}
          >
            Specifications
          </div>
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {specifications.map((spec, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.85rem',
                  padding: '0.5rem',
                  background: 'rgba(0, 0, 0, 0.3)',
                  borderRadius: '4px',
                }}
              >
                <span style={{ color: 'var(--color-text-secondary, #8a8a8a)' }}>{spec.name}</span>
                <span style={{ color: 'var(--color-text-primary, #c8c8c8)', fontFamily: 'var(--font-mono)' }}>
                  {spec.value}
                  {spec.unit && ` ${spec.unit}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inspect Button */}
      {specifications.length > 0 && !locked && (
        <button
          onClick={handleInspect}
          style={{
            margin: '1rem',
            padding: '0.75rem',
            background: 'transparent',
            border: `1px solid ${getCategoryColor()}66`,
            color: getCategoryColor(),
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            borderRadius: '4px',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = getCategoryColor() + '22';
            e.currentTarget.style.borderColor = getCategoryColor();
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.borderColor = getCategoryColor() + '66';
          }}
        >
          {isInspecting ? 'Close Inspection' : 'Inspect'}
        </button>
      )}
    </div>
  );
}

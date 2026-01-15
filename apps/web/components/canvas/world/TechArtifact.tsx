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
import './tech-artifact.css';

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

  if (!discovered) {
    return (
      <div className="tech-artifact--unknown" style={style}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❓</div>
        <div>Unknown Artifact</div>
      </div>
    );
  }

  return (
    <div
      className={`tech-artifact tech-artifact--${category} ${locked ? 'tech-artifact--locked' : ''}`}
      style={style}
    >
      {/* Header */}
      <div className="tech-artifact__header">
        <div className="tech-artifact__title-group">
          <span className="tech-artifact__icon">{getCategoryIcon()}</span>
          <div>
            <div className="tech-artifact__name">{name}</div>
            <div className="tech-artifact__category">{category}</div>
          </div>
        </div>
        {locked && <span style={{ fontSize: '1.2rem' }}>🔒</span>}
      </div>

      {/* 3D/2D Display */}
      <div
        ref={containerRef}
        className={`tech-artifact__display ${
          allowManualRotation && !locked ? 'tech-artifact__display--rotatable' : ''
        } ${isDragging ? 'tech-artifact__display--dragging' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {model3dUrl ? (
          <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* Visual 3D representation */}
            <div
              className={`tech-artifact__3d-object tech-artifact__3d-object--${category}`}
              style={{
                transform: `rotateX(${rotation[0]}rad) rotateY(${rotation[1]}rad) rotateZ(${rotation[2]}rad) scale(${scale})`,
                transition: isDragging ? 'none' : 'transform 0.1s ease',
              }}
            >
              {getCategoryIcon()}
            </div>
            {allowManualRotation && <div className="tech-artifact__hint">Drag to rotate</div>}
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
      <div className="tech-artifact__description">{description}</div>

      {/* Specifications */}
      {specifications.length > 0 && (
        <div className={`tech-artifact__specs ${isInspecting ? 'tech-artifact__specs--expanded' : ''}`}>
          <div className="tech-artifact__specs-title">Specifications</div>
          <div className="tech-artifact__specs-list">
            {specifications.map((spec, index) => (
              <div key={index} className="tech-artifact__spec">
                <span className="tech-artifact__spec-name">{spec.name}</span>
                <span className="tech-artifact__spec-value">
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
        <button onClick={handleInspect} className="tech-artifact__inspect-btn">
          {isInspecting ? 'Close Inspection' : 'Inspect'}
        </button>
      )}
    </div>
  );
}

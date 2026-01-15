/**
 * InteractiveWorldMap - Locations as visual points on illustrated map
 *
 * Features:
 * - SVG-based map with location markers
 * - Hover previews with location details
 * - Connection paths between locations
 * - Zoom and pan support
 * - Responsive to different map sizes
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import type { InteractiveWorldMapProps, Location, Connection } from './types';

export function InteractiveWorldMap({
  worldId,
  locations,
  connections = [],
  selectedLocation,
  hoveredLocation: externalHoveredLocation,
  mapImageUrl,
  viewBox = [0, 0, 100, 100],
  showLabels = true,
  showConnections = true,
  allowZoom = true,
  allowPan = true,
  onLocationClick,
  onLocationHover,
  onConnectionClick,
  style,
}: InteractiveWorldMapProps) {
  const [internalHoveredLocation, setInternalHoveredLocation] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  const hoveredLocation = externalHoveredLocation || internalHoveredLocation;

  // Handle location hover
  const handleLocationHover = useCallback(
    (locationId: string | null) => {
      setInternalHoveredLocation(locationId);
      if (onLocationHover) {
        onLocationHover(locationId);
      }
    },
    [onLocationHover]
  );

  // Handle location click
  const handleLocationClick = useCallback(
    (locationId: string) => {
      if (onLocationClick) {
        onLocationClick(locationId);
      }
    },
    [onLocationClick]
  );

  // Handle connection click
  const handleConnectionClick = useCallback(
    (connectionId: string) => {
      if (onConnectionClick) {
        onConnectionClick(connectionId);
      }
    },
    [onConnectionClick]
  );

  // Pan handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!allowPan) return;
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    },
    [allowPan, pan]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isPanning || !allowPan) return;
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    },
    [isPanning, allowPan, panStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Zoom handler
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (!allowZoom) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom((prev) => Math.max(0.5, Math.min(3, prev * delta)));
    },
    [allowZoom]
  );

  // Get location marker color based on state
  const getLocationColor = (location: Location): string => {
    if (location.id === selectedLocation) return 'var(--color-cyan, #00ffff)';
    if (location.id === hoveredLocation) return 'var(--color-teal, #00ffcc)';
    if (location.locked) return 'var(--color-text-tertiary, #5a5a5a)';
    if (!location.discovered) return 'var(--color-text-secondary, #8a8a8a)';
    return 'var(--color-teal, #00ffcc)';
  };

  // Get connection path
  const getConnectionPath = (connection: Connection): string => {
    const fromLocation = locations.find((loc) => loc.id === connection.from);
    const toLocation = locations.find((loc) => loc.id === connection.to);

    if (!fromLocation || !toLocation) return '';

    const [x1, y1] = fromLocation.position;
    const [x2, y2] = toLocation.position;

    // Convert normalized coordinates (0-1) to viewBox coordinates
    const vbX1 = viewBox[0] + x1 * viewBox[2];
    const vbY1 = viewBox[1] + y1 * viewBox[3];
    const vbX2 = viewBox[0] + x2 * viewBox[2];
    const vbY2 = viewBox[1] + y2 * viewBox[3];

    // Create a curved path
    const midX = (vbX1 + vbX2) / 2;
    const midY = (vbY1 + vbY2) / 2;
    const dx = vbX2 - vbX1;
    const dy = vbY2 - vbY1;
    const offset = Math.sqrt(dx * dx + dy * dy) * 0.1;

    return `M ${vbX1} ${vbY1} Q ${midX + offset} ${midY - offset} ${vbX2} ${vbY2}`;
  };

  return (
    <div
      className="interactive-world-map"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        background: 'var(--color-bg, #000000)',
        ...style,
      }}
    >
      <svg
        ref={svgRef}
        viewBox={viewBox.join(' ')}
        style={{
          width: '100%',
          height: '100%',
          cursor: isPanning ? 'grabbing' : allowPan ? 'grab' : 'default',
          transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
          transition: isPanning ? 'none' : 'transform 0.3s ease',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        {/* Background map image */}
        {mapImageUrl && (
          <image
            href={mapImageUrl}
            x={viewBox[0]}
            y={viewBox[1]}
            width={viewBox[2]}
            height={viewBox[3]}
            opacity={0.3}
            style={{ pointerEvents: 'none' }}
          />
        )}

        {/* Connections */}
        {showConnections &&
          connections.map((connection) => {
            if (!connection.discovered) return null;

            return (
              <path
                key={connection.id}
                d={getConnectionPath(connection)}
                fill="none"
                stroke="rgba(0, 255, 204, 0.3)"
                strokeWidth="0.5"
                strokeDasharray="2,2"
                style={{
                  cursor: onConnectionClick ? 'pointer' : 'default',
                  transition: 'stroke 0.2s ease',
                }}
                onClick={() => handleConnectionClick(connection.id)}
              />
            );
          })}

        {/* Location markers */}
        {locations.map((location) => {
          const [x, y] = location.position;
          const vbX = viewBox[0] + x * viewBox[2];
          const vbY = viewBox[1] + y * viewBox[3];
          const color = getLocationColor(location);
          const isSelected = location.id === selectedLocation;
          const isHovered = location.id === hoveredLocation;

          return (
            <g
              key={location.id}
              style={{ cursor: location.locked ? 'not-allowed' : 'pointer' }}
              onMouseEnter={() => handleLocationHover(location.id)}
              onMouseLeave={() => handleLocationHover(null)}
              onClick={() => !location.locked && handleLocationClick(location.id)}
            >
              {/* Glow effect for selected/hovered */}
              {(isSelected || isHovered) && (
                <circle
                  cx={vbX}
                  cy={vbY}
                  r="3"
                  fill={color}
                  opacity={0.2}
                  style={{
                    animation: 'pulse 2s ease-in-out infinite',
                  }}
                />
              )}

              {/* Main marker */}
              <circle
                cx={vbX}
                cy={vbY}
                r={isSelected ? '1.5' : isHovered ? '1.2' : '1'}
                fill={color}
                stroke={isSelected ? color : 'rgba(255, 255, 255, 0.1)'}
                strokeWidth="0.2"
                style={{
                  transition: 'all 0.2s ease',
                  filter: location.locked ? 'grayscale(100%)' : 'none',
                }}
              />

              {/* Icon */}
              {location.icon && (
                <text
                  x={vbX}
                  y={vbY + 0.3}
                  fontSize="1"
                  textAnchor="middle"
                  fill="var(--color-bg, #000000)"
                  style={{ pointerEvents: 'none' }}
                >
                  {location.icon}
                </text>
              )}

              {/* Label */}
              {showLabels && (isHovered || isSelected || location.discovered) && (
                <text
                  x={vbX}
                  y={vbY - 2}
                  fontSize="1.5"
                  textAnchor="middle"
                  fill={color}
                  fontFamily="var(--font-mono)"
                  style={{
                    pointerEvents: 'none',
                    textShadow: '0 0 4px rgba(0, 0, 0, 0.8)',
                  }}
                >
                  {location.name}
                </text>
              )}

              {/* Locked indicator */}
              {location.locked && (
                <text
                  x={vbX}
                  y={vbY + 0.3}
                  fontSize="1.2"
                  textAnchor="middle"
                  fill={color}
                  style={{ pointerEvents: 'none' }}
                >
                  🔒
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Hover preview */}
      {hoveredLocation && (
        <div
          className="location-preview"
          style={{
            position: 'absolute',
            bottom: '1rem',
            left: '1rem',
            maxWidth: '300px',
            padding: '1rem',
            background: 'rgba(10, 10, 10, 0.95)',
            border: '1px solid rgba(0, 255, 204, 0.3)',
            borderRadius: '4px',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.9rem',
            color: 'var(--color-text-primary, #c8c8c8)',
            pointerEvents: 'none',
          }}
        >
          {(() => {
            const location = locations.find((loc) => loc.id === hoveredLocation);
            if (!location) return null;

            return (
              <>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '1rem',
                    color: 'var(--color-teal, #00ffcc)',
                    marginBottom: '0.5rem',
                  }}
                >
                  {location.name}
                </div>
                {location.description && (
                  <div style={{ color: 'var(--color-text-secondary, #8a8a8a)', fontSize: '0.85rem' }}>
                    {location.description}
                  </div>
                )}
                {location.type && (
                  <div
                    style={{
                      marginTop: '0.5rem',
                      fontSize: '0.75rem',
                      color: 'var(--color-text-tertiary, #5a5a5a)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                    }}
                  >
                    {location.type}
                  </div>
                )}
              </>
            );
          })()}
        </div>
      )}

      {/* Controls hint */}
      {(allowZoom || allowPan) && (
        <div
          style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(10, 10, 10, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            color: 'var(--color-text-tertiary, #5a5a5a)',
            pointerEvents: 'none',
          }}
        >
          {allowZoom && 'Scroll to zoom • '}
          {allowPan && 'Drag to pan'}
        </div>
      )}

      <style jsx>{`
        @keyframes pulse {
          0%,
          100% {
            opacity: 0.2;
            transform: scale(1);
          }
          50% {
            opacity: 0.4;
            transform: scale(1.5);
          }
        }
      `}</style>
    </div>
  );
}

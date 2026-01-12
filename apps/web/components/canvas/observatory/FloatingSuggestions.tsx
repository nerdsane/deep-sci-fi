'use client';

import { useRef, useMemo, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';

export interface Suggestion {
  id: string;
  text: string;
  type: 'explore' | 'create' | 'discover' | 'continue';
  priority: 'low' | 'medium' | 'high';
  worldId?: string;
}

interface FloatingSuggestionsProps {
  suggestions: Suggestion[];
  agentPosition: [number, number, number];
  onSuggestionClick?: (suggestion: Suggestion) => void;
  onDismiss?: (suggestion: Suggestion) => void;
}

// Individual floating suggestion bubble
function SuggestionBubble({
  suggestion,
  position,
  delay,
  onClick,
  onDismiss,
}: {
  suggestion: Suggestion;
  position: THREE.Vector3;
  delay: number;
  onClick?: () => void;
  onDismiss?: () => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const startTime = useRef(Date.now());
  const baseY = useRef(position.y);

  // Fade in after delay
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  // Gentle floating animation
  useFrame((state) => {
    if (!groupRef.current) return;

    const elapsed = (Date.now() - startTime.current) / 1000;

    // Float up and down gently
    groupRef.current.position.y = baseY.current + Math.sin(elapsed * 0.5) * 0.15;

    // Subtle rotation toward camera
    if (isHovered) {
      groupRef.current.scale.lerp(new THREE.Vector3(1.1, 1.1, 1.1), 0.1);
    } else {
      groupRef.current.scale.lerp(new THREE.Vector3(1, 1, 1), 0.1);
    }
  });

  // Icon based on suggestion type
  const getIcon = () => {
    switch (suggestion.type) {
      case 'explore': return '◇';
      case 'create': return '✦';
      case 'discover': return '⟡';
      case 'continue': return '→';
      default: return '•';
    }
  };

  // Color based on priority
  const getColor = () => {
    switch (suggestion.priority) {
      case 'high': return '#00ffcc';
      case 'medium': return '#88ddff';
      case 'low': return '#aabbcc';
      default: return '#88ddff';
    }
  };

  if (!isVisible) return null;

  return (
    <group ref={groupRef} position={position}>
      {/* Connection line to agent */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array([0, 0, 0, -position.x * 0.3, -position.y * 0.2, -position.z * 0.3]), 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color={getColor()}
          transparent
          opacity={0.15}
          blending={THREE.AdditiveBlending}
        />
      </line>

      {/* Glow sphere behind suggestion */}
      <mesh>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshBasicMaterial
          color={getColor()}
          transparent
          opacity={isHovered ? 0.2 : 0.1}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* HTML content */}
      <Html
        center
        style={{
          transition: 'all 0.3s ease',
          opacity: isVisible ? 1 : 0,
          transform: `scale(${isVisible ? 1 : 0.8})`,
          pointerEvents: 'auto',
        }}
      >
        <div
          className="floating-suggestion"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onClick={onClick}
          style={{
            background: 'rgba(0, 0, 0, 0.85)',
            border: `1px solid ${getColor()}40`,
            padding: '10px 14px',
            borderRadius: '4px',
            maxWidth: '200px',
            cursor: 'pointer',
            backdropFilter: 'blur(10px)',
            boxShadow: isHovered
              ? `0 0 20px ${getColor()}30`
              : 'none',
            transition: 'all 0.3s ease',
          }}
        >
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
          }}>
            <span style={{
              color: getColor(),
              fontSize: '14px',
              lineHeight: 1,
              flexShrink: 0,
            }}>
              {getIcon()}
            </span>
            <p style={{
              fontFamily: 'var(--font-sans)',
              fontSize: '12px',
              color: '#c8c8c8',
              margin: 0,
              lineHeight: 1.4,
            }}>
              {suggestion.text}
            </p>
          </div>

          {/* Dismiss button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDismiss?.();
            }}
            style={{
              position: 'absolute',
              top: '-6px',
              right: '-6px',
              width: '16px',
              height: '16px',
              background: 'rgba(0, 0, 0, 0.9)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '50%',
              color: 'rgba(255, 255, 255, 0.5)',
              fontSize: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: isHovered ? 1 : 0,
              transition: 'opacity 0.2s ease',
            }}
          >
            ×
          </button>
        </div>
      </Html>
    </group>
  );
}

export function FloatingSuggestions({
  suggestions,
  agentPosition,
  onSuggestionClick,
  onDismiss,
}: FloatingSuggestionsProps) {
  // Calculate positions around the agent
  const positions = useMemo(() => {
    return suggestions.map((_, index) => {
      const total = suggestions.length;
      const angle = (index / total) * Math.PI * 0.8 - Math.PI * 0.4; // Arc from -40° to +40°
      const radius = 2 + index * 0.5; // Increasing radius
      const height = 0.5 + Math.sin(index * 1.2) * 1;

      return new THREE.Vector3(
        agentPosition[0] + Math.cos(angle) * radius,
        agentPosition[1] + height,
        agentPosition[2] + Math.sin(angle) * radius * 0.5
      );
    });
  }, [suggestions.length, agentPosition]);

  return (
    <group>
      {suggestions.map((suggestion, index) => (
        <SuggestionBubble
          key={suggestion.id}
          suggestion={suggestion}
          position={positions[index]}
          delay={index * 300} // Stagger appearance
          onClick={() => onSuggestionClick?.(suggestion)}
          onDismiss={() => onDismiss?.(suggestion)}
        />
      ))}
    </group>
  );
}

// Hook to manage suggestions state
export function useSuggestions() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isThinking, setIsThinking] = useState(false);

  const addSuggestion = (suggestion: Omit<Suggestion, 'id'>) => {
    const newSuggestion: Suggestion = {
      ...suggestion,
      id: `suggestion-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    };
    setSuggestions(prev => [...prev.slice(-4), newSuggestion]); // Keep max 5
  };

  const removeSuggestion = (id: string) => {
    setSuggestions(prev => prev.filter(s => s.id !== id));
  };

  const clearSuggestions = () => {
    setSuggestions([]);
  };

  // Simulate agent "thinking" before suggestion
  const generateSuggestion = async (
    type: Suggestion['type'],
    context?: { worldCount?: number; hoveredWorld?: string }
  ) => {
    setIsThinking(true);

    // Simulate delay (would be API call in production)
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));

    // Context-aware suggestions
    let text = '';
    let priority: Suggestion['priority'] = 'medium';

    if (type === 'explore') {
      if (context?.worldCount === 0) {
        text = 'The observatory is empty. Create your first world to begin exploring.';
        priority = 'high';
      } else if (context?.hoveredWorld) {
        text = `There's more to discover in this world. Want to dive deeper?`;
        priority = 'medium';
      } else {
        text = 'Each world holds secrets. Hover over one to peek inside.';
        priority = 'low';
      }
    } else if (type === 'create') {
      text = 'I can help you build a new world. What genre calls to you?';
      priority = 'medium';
    } else if (type === 'discover') {
      text = 'Some worlds have unexplored corners. Shall we map them together?';
      priority = 'low';
    } else if (type === 'continue') {
      text = 'Welcome back. Ready to continue where we left off?';
      priority = 'high';
    }

    setIsThinking(false);
    addSuggestion({ text, type, priority });
  };

  return {
    suggestions,
    isThinking,
    addSuggestion,
    removeSuggestion,
    clearSuggestions,
    generateSuggestion,
  };
}

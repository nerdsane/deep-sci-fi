/**
 * CentralHub - Foundation Rules Display
 *
 * The central hub where users land when entering a world.
 * Foundation rules float around the center as interactive panels.
 */

'use client';

import { useRef, useMemo, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, Billboard } from '@react-three/drei';
import * as THREE from 'three';
import type { CentralHubProps, RulePanelProps } from './types';
import type { Rule } from '@/types/dsf';

// Layout constants
const HUB_RADIUS = 6;
const RULE_HEIGHT_BASE = 1.5;
const RULE_HEIGHT_STEP = 0.4;

/**
 * WorldCore - Central glowing orb representing the world's core
 */
function WorldCore() {
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      // Gentle pulse
      const scale = 1 + Math.sin(state.clock.elapsedTime * 0.5) * 0.05;
      meshRef.current.scale.setScalar(scale);
    }
    if (glowRef.current) {
      // Counter-rotate glow
      glowRef.current.rotation.y += 0.002;
      glowRef.current.rotation.z += 0.001;
    }
  });

  return (
    <group>
      {/* Inner core */}
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[0.8, 2]} />
        <meshStandardMaterial
          color="#00ffcc"
          emissive="#00aa88"
          emissiveIntensity={0.6}
          wireframe
        />
      </mesh>

      {/* Outer glow shell */}
      <mesh ref={glowRef} scale={1.3}>
        <icosahedronGeometry args={[0.8, 1]} />
        <meshBasicMaterial
          color="#00ffcc"
          transparent
          opacity={0.1}
          wireframe
        />
      </mesh>

      {/* Core light */}
      <pointLight color="#00ffcc" intensity={2} distance={15} />
    </group>
  );
}

/**
 * RulePanel - Individual floating rule display
 */
function RulePanel({
  rule,
  position,
  index,
  isHovered,
  onClick,
  onHover,
}: RulePanelProps) {
  const groupRef = useRef<THREE.Group>(null);

  // Gentle floating animation
  useFrame((state) => {
    if (groupRef.current) {
      const offset = Math.sin(state.clock.elapsedTime * 0.8 + index) * 0.1;
      groupRef.current.position.y = position.y + offset;
    }
  });

  // Certainty badge colors
  const certaintyColor = useMemo(() => {
    switch (rule.certainty) {
      case 'fundamental':
        return '#00ffcc';
      case 'established':
        return '#00aaff';
      case 'tentative':
        return '#ffaa00';
      default:
        return '#888888';
    }
  }, [rule.certainty]);

  return (
    <group ref={groupRef} position={[position.x, position.y, position.z]}>
      <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
        <Html
          center
          style={{
            pointerEvents: 'auto',
            transition: 'transform 0.3s ease, opacity 0.3s ease',
            transform: isHovered ? 'scale(1.05)' : 'scale(1)',
          }}
        >
          <div
            className={`rule-panel-3d ${isHovered ? 'rule-panel-3d--hovered' : ''}`}
            onPointerEnter={() => onHover?.(true)}
            onPointerLeave={() => onHover?.(false)}
            onClick={onClick}
            style={{
              background: isHovered
                ? 'rgba(0, 255, 204, 0.15)'
                : 'rgba(10, 10, 10, 0.9)',
              border: `1px solid ${isHovered ? '#00ffcc' : 'rgba(0, 255, 204, 0.3)'}`,
              borderRadius: '0',
              padding: '16px 20px',
              maxWidth: '280px',
              cursor: 'pointer',
              boxShadow: isHovered
                ? '0 0 30px rgba(0, 255, 204, 0.3)'
                : '0 0 10px rgba(0, 0, 0, 0.5)',
            }}
          >
            {/* Certainty badge */}
            <div
              style={{
                display: 'inline-block',
                padding: '2px 8px',
                marginBottom: '8px',
                fontSize: '10px',
                fontFamily: 'var(--font-mono, monospace)',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: certaintyColor,
                border: `1px solid ${certaintyColor}`,
                opacity: 0.9,
              }}
            >
              {rule.certainty}
            </div>

            {/* Rule statement */}
            <p
              style={{
                margin: 0,
                fontSize: '13px',
                lineHeight: 1.5,
                color: '#c8c8c8',
                fontFamily: 'var(--font-sans, system-ui)',
              }}
            >
              {rule.statement}
            </p>

            {/* Scope indicator */}
            {rule.scope && rule.scope !== 'universal' && (
              <div
                style={{
                  marginTop: '8px',
                  fontSize: '10px',
                  color: '#666',
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                Scope: {rule.scope}
              </div>
            )}

            {/* Implications (shown on hover) */}
            {isHovered && rule.implications && rule.implications.length > 0 && (
              <div
                style={{
                  marginTop: '12px',
                  paddingTop: '12px',
                  borderTop: '1px solid rgba(0, 255, 204, 0.2)',
                }}
              >
                <div
                  style={{
                    fontSize: '10px',
                    color: '#00ffcc',
                    marginBottom: '6px',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  IMPLICATIONS
                </div>
                <ul
                  style={{
                    margin: 0,
                    padding: '0 0 0 16px',
                    fontSize: '11px',
                    color: '#999',
                  }}
                >
                  {rule.implications.slice(0, 3).map((imp, i) => (
                    <li key={i} style={{ marginBottom: '4px' }}>
                      {imp}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Html>
      </Billboard>

      {/* Connection line to center */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([0, 0, 0, -position.x, -position.y, -position.z])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color="#00ffcc"
          transparent
          opacity={isHovered ? 0.4 : 0.15}
        />
      </line>
    </group>
  );
}

/**
 * CentralHub - Main component
 */
export function CentralHub({ rules, onRuleClick, onRuleHover }: CentralHubProps) {
  const [hoveredRuleId, setHoveredRuleId] = useState<string | null>(null);

  // Calculate positions for rules in a semicircle around the hub
  const rulePositions = useMemo(() => {
    if (!rules || rules.length === 0) return [];

    return rules.map((rule, i) => {
      // Arrange in a semicircle facing the camera (positive Z)
      const totalRules = rules.length;
      const arcSpan = Math.PI * 0.8; // 144 degrees
      const startAngle = -arcSpan / 2;
      const angle = startAngle + (arcSpan / (totalRules + 1)) * (i + 1);

      return {
        rule,
        position: new THREE.Vector3(
          Math.sin(angle) * HUB_RADIUS,
          RULE_HEIGHT_BASE + i * RULE_HEIGHT_STEP,
          Math.cos(angle) * HUB_RADIUS * 0.3 - 2 // Slight curve toward camera
        ),
      };
    });
  }, [rules]);

  // Handle empty rules
  if (!rules || rules.length === 0) {
    return (
      <group>
        <WorldCore />
        <Html position={[0, 2, 0]} center>
          <div
            style={{
              padding: '20px 30px',
              background: 'rgba(10, 10, 10, 0.9)',
              border: '1px solid rgba(0, 255, 204, 0.3)',
              color: '#666',
              fontFamily: 'var(--font-mono, monospace)',
              fontSize: '12px',
              textAlign: 'center',
            }}
          >
            <div style={{ color: '#00ffcc', marginBottom: '8px' }}>
              FOUNDATION UNDEFINED
            </div>
            <div>This world has no rules yet.</div>
            <div style={{ marginTop: '8px', color: '#888' }}>
              Begin a story to discover them.
            </div>
          </div>
        </Html>
      </group>
    );
  }

  return (
    <group>
      {/* Central world core */}
      <WorldCore />

      {/* Foundation rules panels */}
      {rulePositions.map(({ rule, position }, i) => (
        <RulePanel
          key={rule.id}
          rule={rule}
          position={position}
          index={i}
          isHovered={hoveredRuleId === rule.id}
          onClick={() => onRuleClick?.(rule)}
          onHover={(hovered) => {
            setHoveredRuleId(hovered ? rule.id : null);
            onRuleHover?.(hovered ? rule : null);
          }}
        />
      ))}

      {/* Hub label */}
      <Html position={[0, -1, 0]} center>
        <div
          style={{
            padding: '8px 16px',
            background: 'rgba(0, 0, 0, 0.7)',
            border: '1px solid rgba(0, 255, 204, 0.2)',
            color: '#00ffcc',
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '11px',
            letterSpacing: '2px',
            textTransform: 'uppercase',
          }}
        >
          Foundation
        </div>
      </Html>
    </group>
  );
}

export default CentralHub;

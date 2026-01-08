/**
 * RawJsx - Wildcard component that renders arbitrary JSX
 *
 * Transforms and executes JSX code at runtime using Babel standalone.
 * Agent can send any React component code and it will be rendered.
 *
 * Security: The scope is limited to React and DSF utilities.
 * The agent is trusted (same as having CLI access).
 */
import React, { useMemo, useState, useEffect, useCallback, useRef, memo } from 'react';
import * as Babel from '@babel/standalone';

// DSF brand colors and utilities available in scope
const DSF = {
  colors: {
    teal: '#00ffcc',
    cyan: '#00ffff',
    bg: '#000000',
    bgSecondary: '#0a0a0a',
    textPrimary: '#c8c8c8',
    textSecondary: '#8a8a8a',
    textTertiary: '#5a5a5a',
    borderSubtle: 'rgba(255, 255, 255, 0.06)',
    borderMedium: 'rgba(255, 255, 255, 0.1)',
  },
  // Common styled components
  styles: {
    card: {
      background: '#0a0a0a',
      border: '1px solid rgba(255, 255, 255, 0.06)',
      padding: '1.5rem',
    },
    heading: {
      fontFamily: 'var(--font-mono)',
      color: '#c8c8c8',
      letterSpacing: '0.02em',
    },
    text: {
      fontFamily: 'var(--font-sans)',
      color: '#8a8a8a',
      lineHeight: 1.7,
    },
    button: {
      background: 'transparent',
      border: '1px solid rgba(0, 255, 204, 0.3)',
      color: '#00ffcc',
      padding: '0.75rem 1.5rem',
      cursor: 'pointer',
      fontFamily: 'var(--font-mono)',
      fontSize: '0.8rem',
      letterSpacing: '0.1em',
    },
    glow: (color = '#00ffcc') => ({
      boxShadow: `0 0 20px ${color}33, 0 0 40px ${color}1a`,
    }),
  },
};

// Scope of available variables/components in the JSX
const SCOPE: Record<string, any> = {
  // React core
  React,
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
  memo,
  // DSF utilities
  DSF,
  // Shorthand for colors
  colors: DSF.colors,
  styles: DSF.styles,
};

interface RawJsxProps {
  jsx: string;
}

export function RawJsx({ jsx }: RawJsxProps) {
  const Component = useMemo(() => {
    try {
      // Transform JSX to JS using Babel
      const transformed = Babel.transform(jsx, {
        presets: ['react'],
        filename: 'dynamic.jsx',
      });

      if (!transformed.code) {
        throw new Error('Babel transform returned no code');
      }

      // Create function from transformed code
      // The code should be a function component, e.g.: "() => <div>Hello</div>"
      const scopeKeys = Object.keys(SCOPE);
      const scopeValues = Object.values(SCOPE);

      // Wrap in a try-catch for runtime errors
      const wrappedCode = `
        try {
          return (${transformed.code});
        } catch (e) {
          return function ErrorComponent() {
            return React.createElement('div', {
              style: { color: '#ff4444', padding: '1rem', background: '#1a0000', border: '1px solid #ff4444' }
            }, 'Runtime Error: ' + e.message);
          };
        }
      `;

      const fn = new Function(...scopeKeys, wrappedCode);
      const result = fn(...scopeValues);

      // If result is a function (component), use it; otherwise wrap in a component
      if (typeof result === 'function') {
        return result;
      } else if (React.isValidElement(result)) {
        return () => result;
      } else {
        throw new Error('JSX must return a function component or JSX element');
      }
    } catch (err) {
      // Return error component
      return function ErrorFallback() {
        return (
          <div className="raw-jsx-error" style={{
            padding: '1rem',
            background: '#1a0000',
            border: '1px solid #ff4444',
            color: '#ff4444',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
          }}>
            <strong>JSX Error:</strong> {String(err instanceof Error ? err.message : err)}
            <pre style={{ marginTop: '0.5rem', fontSize: '0.75rem', opacity: 0.7, whiteSpace: 'pre-wrap' }}>
              {jsx.slice(0, 200)}{jsx.length > 200 ? '...' : ''}
            </pre>
          </div>
        );
      };
    }
  }, [jsx]);

  return <Component />;
}

// Export scope for documentation
export const RAW_JSX_SCOPE = Object.keys(SCOPE);

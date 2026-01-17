/**
 * AgentUIRenderer - json-render React Renderer
 *
 * Renders agent-generated UI using Vercel's json-render framework.
 * Provides type-safe, security-first component rendering with Zod validation.
 *
 * Key Features:
 * - Component catalog validation (only trusted components)
 * - Zod schema validation (type-safe props)
 * - Action handling (user interactions back to agent)
 * - Streaming support (progressive rendering)
 *
 * Note: Currently using a simplified fallback renderer until we wire up
 * actual React components to the catalog.
 */

'use client';

import React from 'react';
import type { JsonRenderTree } from '@/agent-bus/types';

/**
 * Props for AgentUIRenderer
 */
export interface AgentUIRendererProps {
  /**
   * json-render tree structure
   * Format: { type: string, props: Record<string, unknown>, key: string, children?: JsonRenderTree[] }
   */
  tree: JsonRenderTree;

  /**
   * Callback for user interactions (clicks, form inputs, etc.)
   * Actions are defined in the catalog and validated by Zod schemas.
   *
   * @param action - Action name (e.g., "navigateToWorld", "selectSuggestion")
   * @param params - Action parameters (validated by Zod schema)
   */
  onAction?: (action: string, params: any) => void;

  /**
   * Optional className for styling the renderer container
   */
  className?: string;
}

/**
 * AgentUIRenderer Component
 *
 * Phase 0 implementation: Simplified fallback renderer
 * We'll integrate full json-render + component catalog in next iteration.
 *
 * Example usage:
 * ```tsx
 * <AgentUIRenderer
 *   tree={{
 *     type: 'Button',
 *     props: { label: 'Click me', variant: 'primary', onClick: 'handleClick' },
 *     key: 'button-1'
 *   }}
 *   onAction={(action, params) => {
 *     console.log('Action:', action, params);
 *   }}
 * />
 * ```
 *
 * Security:
 * - Only components in the catalog can be rendered
 * - All props are validated by Zod schemas (when full integration is complete)
 * - Event handlers are string names, not functions (prevents code injection)
 */
export function AgentUIRenderer({
  tree,
  onAction,
  className,
}: AgentUIRendererProps) {
  /**
   * Phase 0: Simplified renderer
   *
   * For now, render a placeholder div with the tree data.
   * Next iteration will integrate full json-render with component registry.
   */
  console.log('[AgentUIRenderer] Rendering tree:', tree);

  if (!tree) {
    return null;
  }

  // Render tree as JSON for debugging (temporary)
  return (
    <div className={`agent-ui-renderer ${className || ''}`}>
      <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded border border-gray-300 dark:border-gray-700">
        <div className="text-sm font-mono text-gray-600 dark:text-gray-400 mb-2">
          json-render tree ({tree.type}):
        </div>
        <pre className="text-xs overflow-auto">
          {JSON.stringify(tree, null, 2)}
        </pre>
        <div className="mt-2 text-xs text-gray-500">
          Phase 0: Simplified renderer. Full component integration coming next.
        </div>
      </div>
    </div>
  );
}

/**
 * Type guards and utilities
 */

/**
 * Check if a tree is valid json-render format
 */
export function isValidTree(tree: any): boolean {
  return (
    tree !== null &&
    typeof tree === 'object' &&
    typeof tree.type === 'string' &&
    typeof tree.key === 'string' &&
    (tree.props === undefined || typeof tree.props === 'object')
  );
}

/**
 * Validate tree structure and log errors
 */
export function validateTree(tree: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!tree) {
    errors.push('Tree is null or undefined');
    return { valid: false, errors };
  }

  if (typeof tree !== 'object') {
    errors.push('Tree must be an object');
    return { valid: false, errors };
  }

  if (typeof tree.type !== 'string') {
    errors.push('Tree.type must be a string');
  }

  if (typeof tree.key !== 'string') {
    errors.push('Tree.key must be a string');
  }

  if (tree.props !== undefined && typeof tree.props !== 'object') {
    errors.push('Tree.props must be an object if provided');
  }

  if (tree.children !== undefined) {
    if (!Array.isArray(tree.children)) {
      errors.push('Tree.children must be an array if provided');
    } else {
      tree.children.forEach((child: any, index: number) => {
        const childValidation = validateTree(child);
        if (!childValidation.valid) {
          errors.push(`Child ${index}: ${childValidation.errors.join(', ')}`);
        }
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Debug utility to log tree structure
 */
export function debugTree(tree: any, indent = 0): void {
  const prefix = '  '.repeat(indent);

  if (!tree) {
    console.log(`${prefix}(null tree)`);
    return;
  }

  console.log(`${prefix}${tree.type} (key: ${tree.key})`);

  if (tree.props) {
    console.log(`${prefix}  props:`, tree.props);
  }

  if (tree.children && Array.isArray(tree.children)) {
    console.log(`${prefix}  children (${tree.children.length}):`);
    tree.children.forEach((child: any) => {
      debugTree(child, indent + 2);
    });
  }
}

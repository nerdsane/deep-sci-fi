/**
 * Agent UI Renderer
 *
 * Renders agent-specified UI components using json-render with type safety and security.
 * All components must be in the registry whitelist.
 */

'use client';

import { Renderer as JsonRenderer, JSONUIProvider } from '@json-render/react';
import type { UITree } from '@json-render/core';
import { componentRegistry } from './registry';
import { catalog } from './catalog';

interface AgentUIRendererProps {
  /**
   * The json-render UITree structure (flat with keys)
   */
  tree: UITree | null;

  /**
   * Callback for handling user interactions with rendered components
   */
  onAction?: (action: { name: string; params: any }) => void;

  /**
   * Whether the tree is currently loading/streaming
   */
  loading?: boolean;
}

/**
 * AgentUIRenderer
 *
 * Renders UI components specified by agents using the json-render protocol.
 *
 * Features:
 * - Type-safe: Props validated with Zod schemas (via catalog)
 * - Secure: Only whitelisted components from registry
 * - Event handling: Interactions sent back via onAction callback
 * - Flat structure: Uses json-render's UITree format
 *
 * @example
 * ```tsx
 * <AgentUIRenderer
 *   tree={{
 *     root: 'btn-1',
 *     elements: {
 *       'btn-1': {
 *         key: 'btn-1',
 *         type: 'Button',
 *         props: { label: 'Click me', onClick: 'handleClick' }
 *       }
 *     }
 *   }}
 *   onAction={(action) => {
 *     console.log('User action:', action.name, action.params);
 *   }}
 * />
 * ```
 */
export function AgentUIRenderer({ tree, onAction, loading }: AgentUIRendererProps) {
  // Convert onAction callback to action handlers map
  const actionHandlers: Record<string, (params: any) => Promise<unknown> | unknown> = {};

  // Create a generic handler that forwards all actions to onAction
  const createHandler = (actionName: string) => {
    return async (params: any) => {
      if (onAction) {
        onAction({ name: actionName, params });
      }
    };
  };

  // Register handlers for all actions in catalog
  if (onAction) {
    Object.keys(catalog.actions || {}).forEach((actionName) => {
      actionHandlers[actionName] = createHandler(actionName);
    });
  }

  return (
    <JSONUIProvider
      registry={componentRegistry}
      actionHandlers={actionHandlers}
    >
      <JsonRenderer
        registry={componentRegistry}
        tree={tree}
        loading={loading}
      />
    </JSONUIProvider>
  );
}

/**
 * Helper to convert simple tree format to UITree format
 * Used for backwards compatibility with existing message format
 */
export function convertToUITree(simpleTree: {
  type: string;
  props: Record<string, unknown>;
  key?: string;
  children?: Array<any>;
}): UITree {
  const elements: Record<string, any> = {};
  let keyCounter = 0;

  function processNode(node: any, parentKey: string | null = null): string {
    const key = node.key || `auto-${keyCounter++}`;
    const element: any = {
      key,
      type: node.type,
      props: node.props,
      parentKey,
    };

    if (node.children && Array.isArray(node.children)) {
      element.children = node.children.map((child: any) => processNode(child, key));
    }

    elements[key] = element;
    return key;
  }

  const rootKey = processNode(simpleTree);

  return {
    root: rootKey,
    elements,
  };
}

// Re-export catalog for type validation if needed
export { catalog };

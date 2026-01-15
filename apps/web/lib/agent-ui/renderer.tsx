/**
 * Agent UI Renderer
 *
 * Renders agent-specified UI components using json-render with type safety and security.
 * All components must be in the catalog whitelist and props are validated with Zod schemas.
 */

'use client';

import { Renderer as JsonRenderer } from '@json-render/react';
import { catalog } from './catalog';

interface AgentUIRendererProps {
  /**
   * The json-render tree structure specifying what to render
   */
  tree: {
    type: string; // Component name from catalog
    props: Record<string, unknown>; // Will be validated by Zod schema
    key?: string;
    children?: Array<any>;
  };

  /**
   * Callback for handling user interactions with rendered components
   */
  onAction?: (action: string, params: any) => void;
}

/**
 * AgentUIRenderer
 *
 * Renders UI components specified by agents using the json-render protocol.
 *
 * Features:
 * - Type-safe: Props validated with Zod schemas
 * - Secure: Only whitelisted components from catalog
 * - Event handling: Interactions sent back via onAction callback
 *
 * @example
 * ```tsx
 * <AgentUIRenderer
 *   tree={{
 *     type: 'Button',
 *     props: { label: 'Click me', onClick: 'handleClick' },
 *     key: 'btn-1'
 *   }}
 *   onAction={(action, params) => {
 *     console.log('User clicked button:', action, params);
 *   }}
 * />
 * ```
 */
export function AgentUIRenderer({ tree, onAction }: AgentUIRendererProps) {
  const handleAction = (action: string, params: any) => {
    if (onAction) {
      onAction(action, params);
    }
  };

  return (
    <JsonRenderer
      catalog={catalog}
      tree={tree}
      onAction={handleAction}
    />
  );
}

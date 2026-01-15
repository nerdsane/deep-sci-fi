/**
 * Component Registry for json-render
 *
 * Maps component type names to React components that work with json-render's API.
 * Each component receives UIElement props and children through ComponentRenderProps.
 */

'use client';

import type { ComponentRegistry, ComponentRenderProps } from '@json-render/react';
import type { UIElement } from '@json-render/core';

// Import UI primitive components
import { DSFDialog } from '@/components/canvas/radix/Dialog';
import { Button } from '@/components/canvas/primitives/Button';
import { Text } from '@/components/canvas/primitives/Text';
import { Image } from '@/components/canvas/primitives/Image';
import { Gallery } from '@/components/canvas/primitives/Gallery';
import { Card } from '@/components/canvas/primitives/Card';
import { Timeline } from '@/components/canvas/primitives/Timeline';
import { Callout } from '@/components/canvas/primitives/Callout';
import { Stats } from '@/components/canvas/primitives/Stats';
import { Badge } from '@/components/canvas/primitives/Badge';
import { Divider } from '@/components/canvas/primitives/Divider';

// Import layout components
import { Stack } from '@/components/canvas/layout/Stack';
import { Grid } from '@/components/canvas/layout/Grid';

// Import experience components
import { Hero, ScrollSection, ProgressBar, ActionBar } from '@/components/canvas/experience';

// Import wildcard component
import { RawJsx } from '@/components/canvas/RawJsx';

// Import Observatory 3D components
import { WorldOrb } from '@/components/canvas/observatory/WorldOrb';
import { StarField } from '@/components/canvas/observatory/StarField';
import { AgentPresence } from '@/components/canvas/observatory/AgentPresence';
import { FloatingSuggestions } from '@/components/canvas/observatory/FloatingSuggestions';

// ============================================================================
// Component Wrappers
// ============================================================================

/**
 * Wrap a component to work with json-render's ComponentRenderProps
 */
function createComponentWrapper<P = Record<string, unknown>>(
  Component: React.ComponentType<P>,
  propMapper?: (element: UIElement, onAction?: (action: any) => void) => P
) {
  return function WrappedComponent({ element, children, onAction }: ComponentRenderProps) {
    const props = propMapper ? propMapper(element, onAction) : (element.props as P);
    return <Component {...props}>{children}</Component>;
  };
}

// ============================================================================
// Registry
// ============================================================================

export const componentRegistry: ComponentRegistry = {
  // UI Primitives
  Button: createComponentWrapper(Button, (element, onAction) => ({
    ...element.props,
    onClick: element.props.onClick && onAction
      ? () => onAction({ name: element.props.onClick as string, params: { componentId: element.key } })
      : element.props.onClick,
    // Type cast safe: Props validated by Zod catalog, converting string event name to function
  } as any)),

  Text: createComponentWrapper(Text),

  Image: createComponentWrapper(Image, (element, onAction) => ({
    ...element.props,
    onClick: element.props.onClick && onAction
      ? () => onAction({ name: element.props.onClick as string, params: { componentId: element.key } })
      : element.props.onClick,
    // Type cast safe: Props validated by Zod catalog, converting string event name to function
  } as any)),

  Gallery: createComponentWrapper(Gallery),

  Card: createComponentWrapper(Card, (element, onAction) => ({
    ...element.props,
    onClick: element.props.onClick && onAction
      ? () => onAction({ name: element.props.onClick as string, params: { componentId: element.key } })
      : element.props.onClick,
    // Type cast safe: Props validated by Zod catalog, converting string event name to function
  } as any)),

  Timeline: createComponentWrapper(Timeline),

  Callout: createComponentWrapper(Callout),

  Stats: createComponentWrapper(Stats),

  Badge: createComponentWrapper(Badge),

  Divider: createComponentWrapper(Divider),

  // Layout
  Stack: createComponentWrapper(Stack),

  Grid: createComponentWrapper(Grid),

  // Experience Components
  Hero: createComponentWrapper(Hero, (element, onAction) => ({
    ...element.props,
    onBadgeClick: element.props.onBadgeClick && onAction
      ? () => onAction({ name: element.props.onBadgeClick as string, params: { componentId: element.key } })
      : element.props.onBadgeClick,
    onScrollClick: element.props.onScrollClick && onAction
      ? () => onAction({ name: element.props.onScrollClick as string, params: { componentId: element.key } })
      : element.props.onScrollClick,
    // Type cast safe: Props validated by Zod catalog, converting string event names to functions
  } as any)),

  ScrollSection: createComponentWrapper(ScrollSection),

  ProgressBar: createComponentWrapper(ProgressBar),

  ActionBar: createComponentWrapper(ActionBar, (element, onAction) => ({
    ...element.props,
    onAction: element.props.onAction && onAction
      ? (actionId: string) => onAction({ name: element.props.onAction as string, params: { componentId: element.key, actionId } })
      : element.props.onAction,
    // Type cast safe: Props validated by Zod catalog, converting string event name to function
  } as any)),

  // Wildcard
  RawJsx: createComponentWrapper(RawJsx),

  // Observatory 3D Components
  WorldOrb: createComponentWrapper(WorldOrb, (element, onAction) => ({
    ...element.props,
    onClick: element.props.onClick && onAction
      ? () => onAction({ name: element.props.onClick as string, params: { worldId: element.props.worldId } })
      : element.props.onClick,
    onHover: element.props.onHover && onAction
      ? () => onAction({ name: element.props.onHover as string, params: { worldId: element.props.worldId } })
      : element.props.onHover,
    // Type cast safe: Props validated by Zod catalog, converting string event names to functions
  } as any)),

  StarField: createComponentWrapper(StarField),

  AgentPresence: createComponentWrapper(AgentPresence),

  FloatingSuggestions: createComponentWrapper(FloatingSuggestions, (element, onAction) => ({
    ...element.props,
    onSuggestionClick: element.props.onSuggestionClick && onAction
      ? (suggestionId: string) => onAction({ name: element.props.onSuggestionClick as string, params: { suggestionId } })
      : element.props.onSuggestionClick,
    onDismiss: element.props.onDismiss && onAction
      ? (suggestionId: string) => onAction({ name: element.props.onDismiss as string, params: { suggestionId } })
      : element.props.onDismiss,
    // Type cast safe: Props validated by Zod catalog, converting string event names to functions
  } as any)),

  // Dialog - Special handling for trigger prop
  Dialog: function DialogWrapper({ element, children, onAction }: ComponentRenderProps) {
    // Type cast safe: Props validated by Zod catalog
    const props = element.props as any;
    return (
      <DSFDialog
        title={props.title}
        description={props.description}
        open={props.open}
        onOpenChange={props.onOpenChange && onAction
          ? (open: boolean) => onAction({ name: props.onOpenChange, params: { componentId: element.key, open } })
          : undefined
        }
      >
        {children}
      </DSFDialog>
    );
  },

  // Phase 3 World Components (Agent B) - TO BE ADDED IN WEEK 2
  // InteractiveWorldMap: createComponentWrapper(...),
  // TechArtifact: createComponentWrapper(...),
  // CharacterReveal: createComponentWrapper(...),
  // StoryPortal: createComponentWrapper(...),
};

/**
 * Agent UI Component Catalog
 *
 * Defines the whitelist of components that agents can render via json-render.
 * Each component has:
 * - A React component implementation
 * - A Zod schema for type-safe prop validation
 * - Children support flag
 *
 * Security: Only components in this catalog can be rendered by agents.
 */

import { createCatalog } from '@json-render/core';
import { z } from 'zod';

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
// Shared Schemas
// ============================================================================

const ActionItemSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string().optional(),
  icon: z.string().optional(),
  variant: z.enum(['primary', 'secondary', 'branch']).optional(),
});

const TimelineEventSchema = z.object({
  id: z.string().optional(),
  date: z.string().optional(),
  year: z.union([z.string(), z.number()]).optional(),
  title: z.string(),
  description: z.string().optional(),
  icon: z.string().optional(),
  status: z.enum(['completed', 'current', 'upcoming']).optional(),
  accent: z.enum(['cyan', 'teal', 'default']).optional(),
});

const GalleryImageSchema = z.object({
  src: z.string(),
  alt: z.string().optional(),
  caption: z.string().optional(),
});

const StatItemSchema = z.object({
  value: z.union([z.string(), z.number()]),
  label: z.string(),
  trend: z.enum(['up', 'down', 'neutral']).optional(),
  accent: z.enum(['cyan', 'teal', 'default']).optional(),
});

// World data schema for WorldOrb
const WorldDataSchema = z.object({
  id: z.string(),
  name: z.string(),
  coverImage: z.string().optional(),
  description: z.string().optional(),
  // Add more world fields as needed
});

// Suggestion schema for FloatingSuggestions
const SuggestionSchema = z.object({
  id: z.string(),
  text: z.string(),
  type: z.enum(['explore', 'create', 'discover', 'continue']),
  priority: z.enum(['high', 'medium', 'low']),
});

// ============================================================================
// Component Catalog
// ============================================================================

export const catalog = createCatalog({
  components: {
    // ==========================================================================
    // UI Primitive Components
    // ==========================================================================

    Dialog: {
      component: DSFDialog,
      props: z.object({
        title: z.string().optional(),
        description: z.string().optional(),
        trigger: z.any().optional(), // ComponentSpec
        open: z.boolean().optional(),
        onOpenChange: z.string().optional(), // Event handler name
      }),
      hasChildren: true,
    },

    Button: {
      component: Button,
      props: z.object({
        label: z.string(),
        variant: z.enum(['primary', 'secondary']).optional(),
        onClick: z.string().optional(), // Event handler name
      }),
      hasChildren: false,
    },

    Text: {
      component: Text,
      props: z.object({
        content: z.string(),
        variant: z.enum(['body', 'heading', 'caption']).optional(),
        size: z.enum(['sm', 'md', 'lg', 'xl', '2xl']).optional(),
        color: z.string().optional(),
      }),
      hasChildren: false,
    },

    Image: {
      component: Image,
      props: z.object({
        src: z.string(),
        alt: z.string().optional(),
        caption: z.string().optional(),
        size: z.enum(['small', 'medium', 'large', 'full']).optional(),
        lightbox: z.boolean().optional(),
        onClick: z.string().optional(), // Event handler name
      }),
      hasChildren: false,
    },

    Gallery: {
      component: Gallery,
      props: z.object({
        images: z.array(GalleryImageSchema),
        columns: z.union([z.literal(2), z.literal(3), z.literal(4)]).optional(),
        gap: z.enum(['sm', 'md', 'lg']).optional(),
        lightbox: z.boolean().optional(),
        variant: z.enum(['grid', 'masonry', 'carousel']).optional(),
      }),
      hasChildren: false,
    },

    Card: {
      component: Card,
      props: z.object({
        title: z.string().optional(),
        subtitle: z.string().optional(),
        image: z.string().optional(),
        imagePosition: z.enum(['top', 'left', 'right']).optional(),
        variant: z.enum(['default', 'elevated', 'outlined', 'ghost']).optional(),
        accent: z.enum(['cyan', 'teal', 'none']).optional(),
        onClick: z.string().optional(), // Event handler name
      }),
      hasChildren: true,
    },

    Timeline: {
      component: Timeline,
      props: z.object({
        events: z.array(TimelineEventSchema),
        orientation: z.enum(['vertical', 'horizontal']).optional(),
        variant: z.enum(['default', 'compact', 'detailed']).optional(),
        showConnectors: z.boolean().optional(),
      }),
      hasChildren: false,
    },

    Callout: {
      component: Callout,
      props: z.object({
        variant: z.enum(['info', 'warning', 'quote', 'rule', 'tech']).optional(),
        title: z.string().optional(),
        content: z.string().optional(),
      }),
      hasChildren: true,
    },

    Stats: {
      component: Stats,
      props: z.object({
        items: z.array(StatItemSchema),
        columns: z.union([z.literal(2), z.literal(3), z.literal(4), z.literal('auto')]).optional(),
        variant: z.enum(['default', 'compact', 'large']).optional(),
      }),
      hasChildren: false,
    },

    Badge: {
      component: Badge,
      props: z.object({
        label: z.string(),
        variant: z.enum(['default', 'cyan', 'teal', 'success', 'warning', 'error']).optional(),
        size: z.enum(['sm', 'md', 'lg']).optional(),
        icon: z.string().optional(),
      }),
      hasChildren: false,
    },

    Divider: {
      component: Divider,
      props: z.object({
        variant: z.enum(['default', 'accent', 'dashed']).optional(),
        spacing: z.enum(['sm', 'md', 'lg']).optional(),
        label: z.string().optional(),
      }),
      hasChildren: false,
    },

    // ==========================================================================
    // Layout Components
    // ==========================================================================

    Stack: {
      component: Stack,
      props: z.object({
        direction: z.enum(['vertical', 'horizontal']).optional(),
        spacing: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
        align: z.enum(['start', 'center', 'end', 'stretch']).optional(),
        justify: z.enum(['start', 'center', 'end', 'between', 'around']).optional(),
        wrap: z.boolean().optional(),
      }),
      hasChildren: true,
    },

    Grid: {
      component: Grid,
      props: z.object({
        columns: z.union([z.number(), z.literal('auto')]).optional(),
        rows: z.union([z.number(), z.literal('auto')]).optional(),
        gap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
        columnGap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
        rowGap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
        minChildWidth: z.string().optional(),
        align: z.enum(['start', 'center', 'end', 'stretch']).optional(),
        justify: z.enum(['start', 'center', 'end', 'stretch']).optional(),
      }),
      hasChildren: true,
    },

    // ==========================================================================
    // Experience Components (Scroll-driven, immersive)
    // ==========================================================================

    Hero: {
      component: Hero,
      props: z.object({
        title: z.string(),
        subtitle: z.string().optional(),
        backgroundImage: z.string().optional(),
        badge: z.string().optional(),
        meta: z.array(z.string()).optional(),
        showScrollIndicator: z.boolean().optional(),
        height: z.enum(['full', 'large', 'medium']).optional(),
        overlay: z.enum(['dark', 'gradient', 'none']).optional(),
        onBadgeClick: z.string().optional(), // Event handler name
        onScrollClick: z.string().optional(), // Event handler name
      }),
      hasChildren: false,
    },

    ScrollSection: {
      component: ScrollSection,
      props: z.object({
        animation: z.enum(['fade-up', 'fade-in', 'slide-left', 'slide-right', 'scale', 'none']).optional(),
        delay: z.number().optional(),
        threshold: z.number().optional(),
      }),
      hasChildren: true,
    },

    ProgressBar: {
      component: ProgressBar,
      props: z.object({
        containerId: z.string().optional(),
        position: z.enum(['top', 'bottom']).optional(),
        height: z.number().optional(),
        showLabel: z.boolean().optional(),
      }),
      hasChildren: false,
    },

    ActionBar: {
      component: ActionBar,
      props: z.object({
        actions: z.array(ActionItemSchema),
        title: z.string().optional(),
        onAction: z.string().optional(), // Event handler name
      }),
      hasChildren: false,
    },

    // ==========================================================================
    // Wildcard Component (Security: Agent has CLI access, this is acceptable)
    // ==========================================================================

    RawJsx: {
      component: RawJsx,
      props: z.object({
        jsx: z.string(), // JSX code to execute
      }),
      hasChildren: false,
    },

    // ==========================================================================
    // Observatory Components (3D/R3F)
    // ==========================================================================

    WorldOrb: {
      component: WorldOrb,
      props: z.object({
        worldId: z.string(),
        world: WorldDataSchema,
        position: z.tuple([z.number(), z.number(), z.number()]),
        scale: z.number().optional().default(1),
        onClick: z.string().optional(), // Event handler name
        onHover: z.string().optional(), // Event handler name
      }),
      hasChildren: false,
    },

    StarField: {
      component: StarField,
      props: z.object({
        count: z.number().optional().default(2000),
        colors: z.array(z.string()).optional(),
      }),
      hasChildren: false,
    },

    AgentPresence: {
      component: AgentPresence,
      props: z.object({
        position: z.tuple([z.number(), z.number(), z.number()]),
        thinking: z.boolean().optional().default(false),
      }),
      hasChildren: false,
    },

    FloatingSuggestions: {
      component: FloatingSuggestions,
      props: z.object({
        agentPosition: z.tuple([z.number(), z.number(), z.number()]),
        suggestions: z.array(SuggestionSchema),
        onSuggestionClick: z.string().optional(), // Event handler name
        onDismiss: z.string().optional(), // Event handler name
      }),
      hasChildren: false,
    },

    // ==========================================================================
    // Phase 3 World Components (Agent B) - TO BE ADDED IN WEEK 2
    // ==========================================================================
    // InteractiveWorldMap: { ... } - Add when Agent B commits component
    // TechArtifact: { ... } - Add when Agent B commits component
    // CharacterReveal: { ... } - Add when Agent B commits component
    // StoryPortal: { ... } - Add when Agent B commits component
  },

  actions: {
    // Navigation actions
    navigateToWorld: {
      params: z.object({
        worldId: z.string(),
      }),
    },

    navigateToStory: {
      params: z.object({
        storyId: z.string(),
        worldId: z.string().optional(),
      }),
    },

    // Suggestion actions
    selectSuggestion: {
      params: z.object({
        suggestionId: z.string(),
      }),
    },

    dismissSuggestion: {
      params: z.object({
        suggestionId: z.string(),
      }),
    },

    // Story actions
    startStory: {
      params: z.object({
        storyId: z.string(),
        worldId: z.string(),
      }),
    },

    continueStory: {
      params: z.object({
        storyId: z.string(),
        segmentId: z.string().optional(),
      }),
    },

    branchStory: {
      params: z.object({
        storyId: z.string(),
        segmentId: z.string(),
        branchId: z.string(),
      }),
    },

    // Generic interaction actions
    click: {
      params: z.object({
        componentId: z.string(),
        data: z.any().optional(),
      }),
    },

    dialogChange: {
      params: z.object({
        componentId: z.string(),
        open: z.boolean(),
      }),
    },

    actionBarAction: {
      params: z.object({
        componentId: z.string(),
        actionId: z.string(),
      }),
    },

    // Phase 3 actions - TO BE ADDED IN WEEK 2
    // exploreLocation: { ... } - Add when Agent B defines interaction model
    // inspectArtifact: { ... } - Add when Agent B defines interaction model
    // revealCharacter: { ... } - Add when Agent B defines interaction model
    // enterPortal: { ... } - Add when Agent B defines interaction model
  },
});

export type ComponentCatalog = typeof catalog;

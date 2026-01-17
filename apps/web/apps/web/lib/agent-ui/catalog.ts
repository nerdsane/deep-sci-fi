/**
 * json-render Component Catalog
 *
 * Defines all trusted UI components that agents can use to create dynamic interfaces.
 * Each component has a Zod schema for type-safe props validation.
 *
 * Security: Components must be explicitly added to this catalog to be renderable.
 * Agents cannot execute arbitrary code - only use pre-approved components.
 */

import { createCatalog } from '@json-render/core';
import { z } from 'zod';

// Import component implementations
// Note: These imports will be added as we integrate with existing components
// For now, we'll define the schemas to establish the catalog structure

// ============================================================================
// Primitives - Basic UI building blocks
// ============================================================================

/**
 * Dialog - Modal dialog with trigger and content
 */
const DialogSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  trigger: z.any().optional(), // Will be refined to ComponentSpec type
  open: z.boolean().optional(),
  onOpenChange: z.string().optional(), // Event handler name
});

/**
 * Button - Click-enabled button with variants
 */
const ButtonSchema = z.object({
  label: z.string(),
  variant: z.enum(['primary', 'secondary']).optional(),
  onClick: z.string().optional(),
});

/**
 * Text - Text content with styling variants
 */
const TextSchema = z.object({
  content: z.string(),
  variant: z.enum(['body', 'heading', 'caption']).optional(),
  size: z.enum(['sm', 'md', 'lg', 'xl', '2xl']).optional(),
  color: z.string().optional(),
});

/**
 * Stack - Flexbox layout container
 */
const StackSchema = z.object({
  direction: z.enum(['vertical', 'horizontal']).optional(),
  spacing: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
  align: z.enum(['start', 'center', 'end', 'stretch']).optional(),
  justify: z.enum(['start', 'center', 'end', 'between', 'around']).optional(),
  wrap: z.boolean().optional(),
});

/**
 * Grid - CSS Grid layout container
 */
const GridSchema = z.object({
  columns: z.union([z.number(), z.literal('auto')]).optional(),
  rows: z.union([z.number(), z.literal('auto')]).optional(),
  gap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
  columnGap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
  rowGap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
  minChildWidth: z.string().optional(),
  align: z.enum(['start', 'center', 'end', 'stretch']).optional(),
  justify: z.enum(['start', 'center', 'end', 'stretch']).optional(),
});

/**
 * Image - Image with lightbox and caption support
 */
const ImageSchema = z.object({
  src: z.string(),
  alt: z.string().optional(),
  caption: z.string().optional(),
  size: z.enum(['small', 'medium', 'large', 'full']).optional(),
  lightbox: z.boolean().optional(),
  onClick: z.string().optional(),
});

/**
 * Gallery - Image collection with multiple layouts
 */
const GalleryImageSchema = z.object({
  src: z.string(),
  alt: z.string().optional(),
  caption: z.string().optional(),
});

const GallerySchema = z.object({
  images: z.array(GalleryImageSchema),
  columns: z.union([z.literal(2), z.literal(3), z.literal(4)]).optional(),
  gap: z.enum(['sm', 'md', 'lg']).optional(),
  lightbox: z.boolean().optional(),
  variant: z.enum(['grid', 'masonry', 'carousel']).optional(),
});

/**
 * Card - Content container with image and variants
 */
const CardSchema = z.object({
  title: z.string().optional(),
  subtitle: z.string().optional(),
  image: z.string().optional(),
  imagePosition: z.enum(['top', 'left', 'right']).optional(),
  variant: z.enum(['default', 'elevated', 'outlined', 'ghost']).optional(),
  accent: z.enum(['cyan', 'teal', 'none']).optional(),
  onClick: z.string().optional(),
});

/**
 * Timeline - Event sequence display
 */
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

const TimelineSchema = z.object({
  events: z.array(TimelineEventSchema),
  orientation: z.enum(['vertical', 'horizontal']).optional(),
  variant: z.enum(['default', 'compact', 'detailed']).optional(),
  showConnectors: z.boolean().optional(),
});

/**
 * Callout - Info/warning/quote boxes
 */
const CalloutSchema = z.object({
  variant: z.enum(['info', 'warning', 'quote', 'rule', 'tech']).optional(),
  title: z.string().optional(),
  content: z.string().optional(),
});

/**
 * Stats - Key metrics display
 */
const StatItemSchema = z.object({
  value: z.union([z.string(), z.number()]),
  label: z.string(),
  trend: z.enum(['up', 'down', 'neutral']).optional(),
  accent: z.enum(['cyan', 'teal', 'default']).optional(),
});

const StatsSchema = z.object({
  items: z.array(StatItemSchema),
  columns: z.union([z.literal(2), z.literal(3), z.literal(4), z.literal('auto')]).optional(),
  variant: z.enum(['default', 'compact', 'large']).optional(),
});

/**
 * Badge - Labels with variants
 */
const BadgeSchema = z.object({
  label: z.string(),
  variant: z.enum(['default', 'cyan', 'teal', 'success', 'warning', 'error']).optional(),
  size: z.enum(['sm', 'md', 'lg']).optional(),
  icon: z.string().optional(),
});

/**
 * Divider - Spacing/sectioning
 */
const DividerSchema = z.object({
  variant: z.enum(['default', 'accent', 'dashed']).optional(),
  spacing: z.enum(['sm', 'md', 'lg']).optional(),
  label: z.string().optional(),
});

// ============================================================================
// Experience Components - Immersive, scroll-driven primitives
// ============================================================================

/**
 * Hero - Full-screen hero section with parallax
 */
const HeroSchema = z.object({
  title: z.string(),
  subtitle: z.string().optional(),
  backgroundImage: z.string().optional(),
  badge: z.string().optional(),
  meta: z.array(z.string()).optional(),
  showScrollIndicator: z.boolean().optional(),
  height: z.enum(['full', 'large', 'medium']).optional(),
  overlay: z.enum(['dark', 'gradient', 'none']).optional(),
  onBadgeClick: z.string().optional(),
  onScrollClick: z.string().optional(),
});

/**
 * ScrollSection - Scroll-triggered animations
 */
const ScrollSectionSchema = z.object({
  animation: z.enum(['fade-up', 'fade-in', 'slide-left', 'slide-right', 'scale', 'none']).optional(),
  delay: z.number().optional(),
  threshold: z.number().optional(),
});

/**
 * ProgressBar - Reading/scroll progress indicator
 */
const ProgressBarSchema = z.object({
  containerId: z.string().optional(),
  position: z.enum(['top', 'bottom']).optional(),
  height: z.number().optional(),
  showLabel: z.boolean().optional(),
});

/**
 * ActionBar - Primary interaction hub with branches
 */
const ActionItemSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string().optional(),
  icon: z.string().optional(),
  variant: z.enum(['primary', 'secondary', 'branch']).optional(),
});

const ActionBarSchema = z.object({
  actions: z.array(ActionItemSchema),
  title: z.string().optional(),
  onAction: z.string().optional(),
});

// ============================================================================
// Create Catalog
// ============================================================================

/**
 * Component catalog for json-render
 *
 * This catalog defines all components that agents can use to create UI.
 * Components not in this catalog cannot be rendered (security).
 *
 * Note: Component implementations will be imported as we integrate
 * with the existing DynamicRenderer components.
 */
export const catalog = createCatalog({
  components: {
    // Primitives (11 components)
    Dialog: {
      component: null as any, // TODO: Import actual component
      props: DialogSchema,
      hasChildren: true,
    },

    Button: {
      component: null as any, // TODO: Import actual component
      props: ButtonSchema,
      hasChildren: false,
    },

    Text: {
      component: null as any, // TODO: Import actual component
      props: TextSchema,
      hasChildren: false,
    },

    Stack: {
      component: null as any, // TODO: Import actual component
      props: StackSchema,
      hasChildren: true,
    },

    Grid: {
      component: null as any, // TODO: Import actual component
      props: GridSchema,
      hasChildren: true,
    },

    Image: {
      component: null as any, // TODO: Import actual component
      props: ImageSchema,
      hasChildren: false,
    },

    Gallery: {
      component: null as any, // TODO: Import actual component
      props: GallerySchema,
      hasChildren: false,
    },

    Card: {
      component: null as any, // TODO: Import actual component
      props: CardSchema,
      hasChildren: true,
    },

    Timeline: {
      component: null as any, // TODO: Import actual component
      props: TimelineSchema,
      hasChildren: false,
    },

    Callout: {
      component: null as any, // TODO: Import actual component
      props: CalloutSchema,
      hasChildren: true,
    },

    Stats: {
      component: null as any, // TODO: Import actual component
      props: StatsSchema,
      hasChildren: false,
    },

    Badge: {
      component: null as any, // TODO: Import actual component
      props: BadgeSchema,
      hasChildren: false,
    },

    Divider: {
      component: null as any, // TODO: Import actual component
      props: DividerSchema,
      hasChildren: false,
    },

    // Experience Components (4 components)
    Hero: {
      component: null as any, // TODO: Import actual component
      props: HeroSchema,
      hasChildren: false,
    },

    ScrollSection: {
      component: null as any, // TODO: Import actual component
      props: ScrollSectionSchema,
      hasChildren: true,
    },

    ProgressBar: {
      component: null as any, // TODO: Import actual component
      props: ProgressBarSchema,
      hasChildren: false,
    },

    ActionBar: {
      component: null as any, // TODO: Import actual component
      props: ActionBarSchema,
      hasChildren: false,
    },

    // Phase 3 components will be added here as Agent B builds them:
    // - InteractiveWorldMap
    // - TechArtifact
    // - CharacterReveal
    // - StoryPortal
  },

  actions: {
    /**
     * Navigate to a specific world
     */
    navigateToWorld: {
      params: z.object({
        worldId: z.string(),
      })
    },

    /**
     * Select a suggestion from FloatingSuggestions
     */
    selectSuggestion: {
      params: z.object({
        suggestionId: z.string(),
      })
    },

    /**
     * Start reading a story
     */
    startStory: {
      params: z.object({
        storyId: z.string(),
        worldId: z.string(),
      })
    },

    /**
     * Continue a story from a specific segment
     */
    continueStory: {
      params: z.object({
        storyId: z.string(),
        segmentId: z.string(),
      })
    },

    /**
     * Select a branch in story navigation
     */
    selectBranch: {
      params: z.object({
        storyId: z.string(),
        branchId: z.string(),
      })
    },

    // Phase 3 actions will be added here:
    // - exploreLocation
    // - inspectArtifact
    // - revealCharacter
    // - enterPortal
  }
});

export type ComponentCatalog = typeof catalog;

/**
 * Export schemas for reuse
 */
export const schemas = {
  // Primitives
  Dialog: DialogSchema,
  Button: ButtonSchema,
  Text: TextSchema,
  Stack: StackSchema,
  Grid: GridSchema,
  Image: ImageSchema,
  Gallery: GallerySchema,
  GalleryImage: GalleryImageSchema,
  Card: CardSchema,
  Timeline: TimelineSchema,
  TimelineEvent: TimelineEventSchema,
  Callout: CalloutSchema,
  Stats: StatsSchema,
  StatItem: StatItemSchema,
  Badge: BadgeSchema,
  Divider: DividerSchema,

  // Experience
  Hero: HeroSchema,
  ScrollSection: ScrollSectionSchema,
  ProgressBar: ProgressBarSchema,
  ActionBar: ActionBarSchema,
  ActionItem: ActionItemSchema,
};

// Component specification types for dynamic rendering

export interface BaseComponentSpec {
  type: string;
  id?: string;
}

export interface DialogSpec extends BaseComponentSpec {
  type: 'Dialog';
  props: {
    title?: string;
    description?: string;
    trigger?: ComponentSpec;
    open?: boolean;
    onOpenChange?: string; // event handler name
  };
  children?: ComponentSpec | ComponentSpec[];
}

export interface ButtonSpec extends BaseComponentSpec {
  type: 'Button';
  props: {
    label: string;
    variant?: 'primary' | 'secondary';
    onClick?: string; // event handler name
  };
}

export interface TextSpec extends BaseComponentSpec {
  type: 'Text';
  props: {
    content: string;
    variant?: 'body' | 'heading' | 'caption';
    size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
    color?: string;
  };
}

export interface StackSpec extends BaseComponentSpec {
  type: 'Stack';
  props: {
    direction?: 'vertical' | 'horizontal';
    spacing?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    align?: 'start' | 'center' | 'end' | 'stretch';
    justify?: 'start' | 'center' | 'end' | 'between' | 'around';
    wrap?: boolean;
  };
  children?: ComponentSpec[];
}

export interface GridSpec extends BaseComponentSpec {
  type: 'Grid';
  props: {
    columns?: number | 'auto';
    rows?: number | 'auto';
    gap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    columnGap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    rowGap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    minChildWidth?: string;
    align?: 'start' | 'center' | 'end' | 'stretch';
    justify?: 'start' | 'center' | 'end' | 'stretch';
  };
  children?: ComponentSpec[];
}

export interface ImageSpec extends BaseComponentSpec {
  type: 'Image';
  props: {
    src: string;
    alt?: string;
    caption?: string;
    size?: 'small' | 'medium' | 'large' | 'full';
    lightbox?: boolean;
    onClick?: string;
  };
}

export interface GalleryImage {
  src: string;
  alt?: string;
  caption?: string;
}

export interface GallerySpec extends BaseComponentSpec {
  type: 'Gallery';
  props: {
    images: GalleryImage[];
    columns?: 2 | 3 | 4;
    gap?: 'sm' | 'md' | 'lg';
    lightbox?: boolean;
    variant?: 'grid' | 'masonry' | 'carousel';
  };
}

export interface CardSpec extends BaseComponentSpec {
  type: 'Card';
  props: {
    title?: string;
    subtitle?: string;
    image?: string;
    imagePosition?: 'top' | 'left' | 'right';
    variant?: 'default' | 'elevated' | 'outlined' | 'ghost';
    accent?: 'cyan' | 'teal' | 'none';
    onClick?: string;
  };
  children?: ComponentSpec | ComponentSpec[];
}

export interface TimelineEvent {
  id?: string;
  date?: string;
  year?: string | number;
  title: string;
  description?: string;
  icon?: string;
  status?: 'completed' | 'current' | 'upcoming';
  accent?: 'cyan' | 'teal' | 'default';
}

export interface TimelineSpec extends BaseComponentSpec {
  type: 'Timeline';
  props: {
    events: TimelineEvent[];
    orientation?: 'vertical' | 'horizontal';
    variant?: 'default' | 'compact' | 'detailed';
    showConnectors?: boolean;
  };
}

export interface CalloutSpec extends BaseComponentSpec {
  type: 'Callout';
  props: {
    variant?: 'info' | 'warning' | 'quote' | 'rule' | 'tech';
    title?: string;
    content?: string;
  };
  children?: ComponentSpec | ComponentSpec[];
}

export interface StatItem {
  value: string | number;
  label: string;
  trend?: 'up' | 'down' | 'neutral';
  accent?: 'cyan' | 'teal' | 'default';
}

export interface StatsSpec extends BaseComponentSpec {
  type: 'Stats';
  props: {
    items: StatItem[];
    columns?: 2 | 3 | 4 | 'auto';
    variant?: 'default' | 'compact' | 'large';
  };
}

export interface BadgeSpec extends BaseComponentSpec {
  type: 'Badge';
  props: {
    label: string;
    variant?: 'default' | 'cyan' | 'teal' | 'success' | 'warning' | 'error';
    size?: 'sm' | 'md' | 'lg';
    icon?: string;
  };
}

export interface DividerSpec extends BaseComponentSpec {
  type: 'Divider';
  props: {
    variant?: 'default' | 'accent' | 'dashed';
    spacing?: 'sm' | 'md' | 'lg';
    label?: string;
  };
}

// ============================================================================
// Experience Components - Scroll-driven, immersive primitives
// ============================================================================

export interface HeroSpec extends BaseComponentSpec {
  type: 'Hero';
  props: {
    title: string;
    subtitle?: string;
    backgroundImage?: string;
    badge?: string;
    meta?: string[];
    showScrollIndicator?: boolean;
    height?: 'full' | 'large' | 'medium';
    overlay?: 'dark' | 'gradient' | 'none';
    onBadgeClick?: string;
    onScrollClick?: string;
  };
}

export interface ScrollSectionSpec extends BaseComponentSpec {
  type: 'ScrollSection';
  props: {
    animation?: 'fade-up' | 'fade-in' | 'slide-left' | 'slide-right' | 'scale' | 'none';
    delay?: number;
    threshold?: number;
  };
  children?: ComponentSpec | ComponentSpec[];
}

export interface ProgressBarSpec extends BaseComponentSpec {
  type: 'ProgressBar';
  props: {
    containerId?: string;
    position?: 'top' | 'bottom';
    height?: number;
    showLabel?: boolean;
  };
}

export interface ActionItemSpec {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'branch';
}

export interface ActionBarSpec extends BaseComponentSpec {
  type: 'ActionBar';
  props: {
    actions: ActionItemSpec[];
    title?: string;
    onAction?: string;
  };
}

// ============================================================================
// Wildcard Component - Full JSX execution
// ============================================================================

export interface RawJsxSpec extends BaseComponentSpec {
  type: 'RawJsx';
  props: {
    jsx: string; // JSX code to render (function component)
  };
}

export type ComponentSpec =
  | DialogSpec
  | ButtonSpec
  | TextSpec
  | StackSpec
  | GridSpec
  | ImageSpec
  | GallerySpec
  | CardSpec
  | TimelineSpec
  | CalloutSpec
  | StatsSpec
  | BadgeSpec
  | DividerSpec
  | HeroSpec
  | ScrollSectionSpec
  | ProgressBarSpec
  | ActionBarSpec
  | RawJsxSpec;

export interface CanvasState {
  rootComponent: ComponentSpec | null;
  version: number;
}

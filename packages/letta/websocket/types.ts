/**
 * Component Spec Types for Canvas UI
 *
 * These types define the structure of UI components that agents can create.
 */

export interface ComponentSpec {
  type: string;
  id?: string;
  props?: Record<string, any>;
  children?: ComponentSpec | ComponentSpec[];
}

// Primitive components
export interface TextSpec extends ComponentSpec {
  type: 'Text';
  props: {
    content: string;
    variant?: 'body' | 'heading' | 'caption' | 'code';
    size?: 'sm' | 'md' | 'lg' | 'xl';
    color?: string;
  };
}

export interface ButtonSpec extends ComponentSpec {
  type: 'Button';
  props: {
    label: string;
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    onClick?: string; // Callback name
  };
}

export interface ImageSpec extends ComponentSpec {
  type: 'Image';
  props: {
    src: string;
    alt?: string;
    caption?: string;
    size?: 'sm' | 'md' | 'lg' | 'full';
    lightbox?: boolean;
    onClick?: string;
  };
}

export interface CardSpec extends ComponentSpec {
  type: 'Card';
  props: {
    title?: string;
    subtitle?: string;
    image?: string;
    imagePosition?: 'top' | 'left' | 'right' | 'background';
    variant?: 'default' | 'elevated' | 'outlined';
    accent?: string;
    onClick?: string;
  };
}

export interface GallerySpec extends ComponentSpec {
  type: 'Gallery';
  props: {
    images: Array<{
      src: string;
      alt?: string;
      caption?: string;
    }>;
    columns?: number;
    gap?: string;
    lightbox?: boolean;
    variant?: 'grid' | 'masonry' | 'carousel';
  };
}

export interface TimelineSpec extends ComponentSpec {
  type: 'Timeline';
  props: {
    events: Array<{
      title: string;
      description?: string;
      date?: string;
      icon?: string;
      color?: string;
    }>;
    orientation?: 'vertical' | 'horizontal';
    variant?: 'default' | 'compact' | 'detailed';
    showConnectors?: boolean;
  };
}

export interface StatsSpec extends ComponentSpec {
  type: 'Stats';
  props: {
    items: Array<{
      label: string;
      value: string | number;
      change?: string;
      trend?: 'up' | 'down' | 'neutral';
    }>;
    columns?: number;
    variant?: 'default' | 'card' | 'inline';
  };
}

export interface CalloutSpec extends ComponentSpec {
  type: 'Callout';
  props: {
    variant?: 'info' | 'warning' | 'success' | 'error' | 'quote';
    title?: string;
    content?: string;
  };
}

export interface BadgeSpec extends ComponentSpec {
  type: 'Badge';
  props: {
    label: string;
    variant?: 'default' | 'primary' | 'success' | 'warning' | 'error';
    size?: 'sm' | 'md' | 'lg';
    icon?: string;
  };
}

export interface DividerSpec extends ComponentSpec {
  type: 'Divider';
  props?: {
    variant?: 'solid' | 'dashed' | 'dotted';
    spacing?: 'sm' | 'md' | 'lg';
    label?: string;
  };
}

// Layout components
export interface StackSpec extends ComponentSpec {
  type: 'Stack';
  props?: {
    direction?: 'horizontal' | 'vertical';
    spacing?: 'none' | 'sm' | 'md' | 'lg';
    align?: 'start' | 'center' | 'end' | 'stretch';
    justify?: 'start' | 'center' | 'end' | 'between' | 'around';
    wrap?: boolean;
  };
  children: ComponentSpec[];
}

export interface GridSpec extends ComponentSpec {
  type: 'Grid';
  props?: {
    columns?: number | string;
    rows?: number | string;
    gap?: string;
    columnGap?: string;
    rowGap?: string;
    minChildWidth?: string;
    align?: 'start' | 'center' | 'end' | 'stretch';
    justify?: 'start' | 'center' | 'end' | 'stretch';
  };
  children: ComponentSpec[];
}

// Experience components
export interface HeroSpec extends ComponentSpec {
  type: 'Hero';
  props: {
    title: string;
    subtitle?: string;
    backgroundImage?: string;
    badge?: string;
    meta?: string;
    showScrollIndicator?: boolean;
    height?: string;
    overlay?: 'none' | 'light' | 'dark' | 'gradient';
    onBadgeClick?: string;
    onScrollClick?: string;
  };
}

export interface ActionBarSpec extends ComponentSpec {
  type: 'ActionBar';
  props: {
    actions: Array<{
      id: string;
      label: string;
      icon?: string;
      variant?: 'primary' | 'secondary' | 'ghost';
    }>;
    title?: string;
    onAction?: string;
  };
}

export interface DialogSpec extends ComponentSpec {
  type: 'Dialog';
  props: {
    title?: string;
    description?: string;
    open?: boolean;
    trigger?: ComponentSpec;
    onOpenChange?: string;
  };
}

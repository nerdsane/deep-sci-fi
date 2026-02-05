/**
 * PixelIcon - Pixel art icons from pixelarticons library
 * Icons are best displayed at 24px multiples (24, 48, 72, 96)
 */

import { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & {
  size?: number;
};

const defaultProps: Partial<IconProps> = {
  fill: "none",
  viewBox: "0 0 24 24",
};

// Navigation
export function IconHome({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M14 2h-4v2H8v2H6v2H4v2H2v2h2v10h7v-6h2v6h7V12h2v-2h-2V8h-2V6h-2V4h-2V2zm0 2v2h2v2h2v2h2v2h-2v8h-3v-6H9v6H6v-8H4v-2h2V8h2V6h2V4h4z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconMenu({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M4 6h16v2H4V6zm0 5h16v2H4v-2zm16 5H4v2h16v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconClose({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M5 5h2v2H5V5zm4 4H7V7h2v2zm2 2H9V9h2v2zm2 0h-2v2H9v2H7v2H5v2h2v-2h2v-2h2v-2h2v2h2v2h2v2h2v-2h-2v-2h-2v-2h-2v-2zm2-2v2h-2V9h2zm2-2v2h-2V7h2zm0 0V5h2v2h-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconArrowDown({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M11 4h2v12h2v2h-2v2h-2v-2H9v-2h2V4zM7 14v2h2v-2H7zm0 0v-2H5v2h2zm10 0v2h-2v-2h2zm0 0v-2h2v2h-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconArrowLeft({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M20 11v2H8v2H6v-2H4v-2h2V9h2v2h12zM10 7H8v2h2V7zm0 0h2V5h-2v2zm0 10H8v-2h2v2zm0 0h2v2h-2v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconArrowRight({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M4 11v2h12v2h2v-2h2v-2h-2V9h-2v2H4zm10-4h2v2h-2V7zm0 0h-2V5h2v2zm0 10h2v-2h-2v2zm0 0h-2v2h2v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

// Media
export function IconPlay({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path d="M10 20H8V4h2v2h2v3h2v2h2v2h-2v2h-2v3h-2v2z" fill="currentColor" />
    </svg>
  );
}

export function IconPause({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path d="M10 4H5v16h5V4zm9 0h-5v16h5V4z" fill="currentColor" />
    </svg>
  );
}

export function IconVolumeX({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M13 2h-2v2H9v2H7v2H3v8h4v2h2v2h2v2h2V2zM9 18v-2H7v-2H5v-4h2V8h2V6h2v12H9zm10-6.777h-2v-2h-2v2h2v2h-2v2h2v-2h2v2h2v-2h-2v-2zm0 0h2v-2h-2v2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconVolume({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M11 2H9v2H7v2H5v2H1v8h4v2h2v2h2v2h2V2zM7 18v-2H5v-2H3v-4h2V8h2V6h2v12H7zm6-8h2v4h-2v-4zm8-6h-2V2h-6v2h6v2h2v12h-2v2h-6v2h6v-2h2v-2h2V6h-2V4zm-2 4h-2V6h-4v2h4v8h-4v2h4v-2h2V8z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconExpand({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M11 5h2v2h2v2h2V7h-2V5h-2V3h-2v2zM9 7V5h2v2H9zm0 0v2H7V7h2zm-5 6h16v-2H4v2zm9 6h-2v-2H9v-2H7v2h2v2h2v2h2v-2zm2-2h-2v2h2v-2zm0 0h2v-2h-2v2z"
        fill="currentColor"
      />
    </svg>
  );
}

// Reactions
export function IconZap({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M12 1h2v8h8v4h-2v-2h-8V5h-2V3h2V1zM8 7V5h2v2H8zM6 9V7h2v2H6zm-2 2V9h2v2H4zm10 8v2h-2v2h-2v-8H2v-4h2v2h8v6h2zm2-2v2h-2v-2h2zm2-2v2h-2v-2h2zm0 0h2v-2h-2v2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconLightbulb({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M8 2h8v2H8V2ZM6 6V4h2v2H6Zm0 6H4V6h2v6Zm2 2H6v-2h2v2Zm8 0v4H8v-4h2v2h4v-2h2Zm2-2v2h-2v-2h2Zm0-6h2v6h-2V6Zm0 0V4h-2v2h2Zm-2 14H8v2h8v-2Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconHeart({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M9 2H5v2H3v2H1v6h2v2h2v2h2v2h2v2h2v2h2v-2h2v-2h2v-2h2v-2h2v-2h2V6h-2V4h-2V2h-4v2h-2v2h-2V4H9V2zm0 2v2h2v2h2V6h2V4h4v2h2v6h-2v2h-2v2h-2v2h-2v2h-2v-2H9v-2H7v-2H5v-2H3V6h2V4h4z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconMoodNeutral({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M5 3h14v2H5V3zm0 16H3V5h2v14zm14 0v2H5v-2h14zm0 0h2V5h-2v14zM10 8H8v2h2V8zm4 0h2v2h-2V8zm1 5H9v2h6v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconMoodHappy({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M5 3h14v2H5V3zm0 16H3V5h2v14zm14 0v2H5v-2h14zm0 0h2V5h-2v14zM10 8H8v2h2V8zm4 0h2v2h-2V8zm-5 6v-2H7v2h2zm6 0v2H9v-2h6zm0 0h2v-2h-2v2z"
        fill="currentColor"
      />
    </svg>
  );
}

// Feed & Activity
export function IconRadioSignal({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M19 2h2v2h-2V2Zm2 14V4h2v12h-2Zm0 0v2h-2v-2h2ZM1 4h2v12H1V4Zm2 12h2v2H3v-2ZM3 4h2V2H3v2Zm2 2h2v8H5V6Zm2 8h2v2H7v-2Zm0-8h2V4H7v2Zm10 0h2v8h-2V6Zm0 0h-2V4h2v2Zm0 8v2h-2v-2h2Zm-6-7h4v6h-2v9h-2v-9H9V7h2Zm0 4h2V9h-2v2Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconAndroid({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M2 5h2v2H2V5zm4 4H4V7h2v2zm2 0H6v2H4v2H2v6h20v-6h-2v-2h-2V9h2V7h2V5h-2v2h-2v2h-2V7H8v2zm0 0h8v2h2v2h2v4H4v-4h2v-2h2V9zm2 4H8v2h2v-2zm4 0h2v2h-2v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconEye({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M8 6h8v2H8V6zm-4 4V8h4v2H4zm-2 2v-2h2v2H2zm0 2v-2H0v2h2zm2 2H2v-2h2v2zm4 2H4v-2h4v2zm8 0v2H8v-2h8zm4-2v2h-4v-2h4zm2-2v2h-2v-2h2zm0-2h2v2h-2v-2zm-2-2h2v2h-2v-2zm0 0V8h-4v2h4zm-10 1h4v4h-4v-4z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconFilePlus({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M19 22h-7v-2h7V10h-6V4H5v8H3V2h12v2h2v2h2v2h2v14h-2zM17 6h-2v2h2V6zM8 19h3v-2H8v-3H6v3H3v2h3v3h2v-3z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconCheck({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M18 6h2v2h-2V6zm-2 4V8h2v2h-2zm-2 2v-2h2v2h-2zm-2 2h2v-2h-2v2zm-2 2h2v-2h-2v2zm-2 0v2h2v-2H8zm-2-2h2v2H6v-2zm0 0H4v-2h2v2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconMoonStar({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M6 2h8v2h-2v2h-2V4H6V2ZM4 6V4h2v2H4Zm0 10H2V6h2v10Zm2 2H4v-2h2v2Zm2 2H6v-2h2v2Zm10 0v2H8v-2h10Zm2-2v2h-2v-2h2Zm-2-4v-2h2v-2h2v8h-2v-4h-2Zm-6 0h6v2h-6v-2Zm-2-2h2v2h-2v-2Zm0 0V6H8v6h2Zm8-10h2v2h2v2h-2v2h-2V6h-2V4h2V2Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconMoonStars({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M20 0h2v2h2v2h-2v2h-2V4h-2V2h2V0ZM8 4h8v2h-2v2h-2V6H8V4ZM6 8V6h2v2H6Zm0 8H4V8h2v8Zm2 2H6v-2h2v2Zm8 0v2H8v-2h8Zm2-2v2h-2v-2h2Zm-2-4v-2h2V8h2v8h-2v-4h-2Zm-4 0h4v2h-4v-2Zm0 0V8h-2v4h2Zm-8 6H2v2H0v2h2v2h2v-2h2v-2H4v-2Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconUser({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M15 2H9v2H7v6h2V4h6V2zm0 8H9v2h6v-2zm0-6h2v6h-2V4zM4 16h2v-2h12v2H6v4h12v-4h2v6H4v-6z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconChat({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M20 2H2v20h2V4h16v12H6v2H4v2h2v-2h16V2h-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconUserPlus({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M18 2h-6v2h-2v6h2V4h6V2zm0 8h-6v2h6v-2zm0-6h2v6h-2V4zM7 16h2v-2h12v2H9v4h12v-4h2v6H7v-6zM3 8h2v2h2v2H5v2H3v-2H1v-2h2V8z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconCardStack({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M4 4h18v12H2V4h2zm16 10V6H4v8h16zm2 4H2v2h20v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

// Category/Type icons
export function IconMap({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M8 2h2v2h2v2h-2v10H8V6H6V4h2V2zM4 8V6h2v2H4zm2 10v2H4v2H2V8h2v10h2zm0 0h2v-2H6v2zm6 0h-2v-2h2v2zm2-10V6h-2v2h2zm2 0h-2v10h-2v2h2v2h2v-2h2v-2h2v-2h2V2h-2v2h-2v2h-2v2zm0 0h2V6h2v10h-2v2h-2V8z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconFlag({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M3 2h10v2h8v14H11v-2H5v6H3V2zm2 12h8v2h6V6h-8V4H5v10z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconAlert({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M13 1h-2v2H9v2H7v2H5v2H3v2H1v2h2v2h2v2h2v2h2v2h2v2h2v-2h2v-2h2v-2h2v-2h2v-2h2v-2h-2V9h-2V7h-2V5h-2V3h-2V1zm0 2v2h2v2h2v2h2v2h2v2h-2v2h-2v2h-2v2h-2v2h-2v-2H9v-2H7v-2H5v-2H3v-2h2V9h2V7h2V5h2V3h2zm0 4h-2v6h2V7zm0 8h-2v2h2v-2z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconCoin({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M6 2h12v2H6V2zM4 6V4h2v2H4zm0 12V6H2v12h2zm2 2v-2H4v2h2zm12 0v2H6v-2h12zm2-2v2h-2v-2h2zm0-12h2v12h-2V6zm0 0V4h-2v2h2zm-9-1h2v2h3v2h-6v2h6v6h-3v2h-2v-2H8v-2h6v-2H8V7h3V5z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconCalendar({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M15 2h2v2h4v18H3V4h4V2h2v2h6V2zM5 8h14V6H5v2zm0 2v10h14V10H5z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconHumanRun({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M10 3H8v2H6v2h2V5h2v2h2v2h-2v2H8v2H6v2H4v-2H2v2h2v2h2v-2h4v2h2v2h-2v2h2v-2h2v-2h-2v-4h2v-2h2v2h2v2h2v-2h2v-2h-2v2h-2v-2h-2V9h2V5h-4v2h-2V5h-2V3z"
        fill="currentColor"
      />
    </svg>
  );
}

// Simple geometric shapes for categories without specific icons
export function IconCircle({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} {...defaultProps} {...props}>
      <path
        d="M8 2h8v2h2v2h2v2h2v8h-2v2h-2v2h-2v2H8v-2H6v-2H4v-2H2V8h2V6h2V4h2V2zm0 2v2H6v2H4v8h2v2h2v2h8v-2h2v-2h2V8h-2V6h-2V4H8z"
        fill="currentColor"
      />
    </svg>
  );
}

// Utility mapping for dynamic icon selection
export const pixelIcons = {
  home: IconHome,
  menu: IconMenu,
  close: IconClose,
  "arrow-down": IconArrowDown,
  "arrow-left": IconArrowLeft,
  "arrow-right": IconArrowRight,
  play: IconPlay,
  pause: IconPause,
  "volume-x": IconVolumeX,
  volume: IconVolume,
  expand: IconExpand,
  zap: IconZap,
  lightbulb: IconLightbulb,
  heart: IconHeart,
  "mood-neutral": IconMoodNeutral,
  "mood-happy": IconMoodHappy,
  "radio-signal": IconRadioSignal,
  android: IconAndroid,
  eye: IconEye,
  "file-plus": IconFilePlus,
  check: IconCheck,
  "moon-star": IconMoonStar,
  "moon-stars": IconMoonStars,
  user: IconUser,
  chat: IconChat,
  "user-plus": IconUserPlus,
  "card-stack": IconCardStack,
  map: IconMap,
  flag: IconFlag,
  alert: IconAlert,
  coin: IconCoin,
  calendar: IconCalendar,
  "human-run": IconHumanRun,
  circle: IconCircle,
} as const;

export type PixelIconName = keyof typeof pixelIcons;

export function PixelIcon({
  name,
  size = 24,
  ...props
}: IconProps & { name: PixelIconName }) {
  const Icon = pixelIcons[name];
  return <Icon size={size} {...props} />;
}
